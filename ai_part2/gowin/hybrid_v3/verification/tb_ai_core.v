`timescale 1ns/1ps
module tb_ai_core;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,start=0;
    reg [47:0] feat=0;
    wire busy,done;
    wire [1:0] class_id;wire [47:0] scores;
    ai_core dut(clk,rst_n,start,feat,busy,done,class_id,scores);
    integer fd,status,expected_class,count,cycles,min_cycles,max_cycles;
    reg [47:0] input_feat,expected_scores;
    reg [1023:0] vectors_path;
    task tick;
        begin @(posedge clk);#1;end
    endtask
    initial begin
        repeat(3) tick;
        @(negedge clk);rst_n=1;start=1;feat=48'h7f7f7f7f7f7f;
        tick;repeat(8) tick;
        // Reset during an inference must abandon the transaction without done.
        @(negedge clk);rst_n=0;start=0;tick;
        if(busy || done) $fatal(1,"reset did not clear busy/done");
        @(negedge clk);rst_n=1;
        if(!$value$plusargs("vectors=%s",vectors_path)) vectors_path="vectors.txt";
        fd=$fopen(vectors_path,"r");
        if(fd==0) $fatal(1,"cannot open vectors");
        count=0;min_cycles=10000;max_cycles=0;
        while(!$feof(fd)) begin
            status=$fscanf(fd,"%h %h %d\n",input_feat,expected_scores,expected_class);
            if(status!=3) $fatal(1,"malformed vector file");
            @(negedge clk);feat=input_feat;start=1;
            tick;
            if(!busy) $fatal(1,"busy not asserted after accepted start");
            @(negedge clk);start=0;feat=~input_feat;
            cycles=0;
            while(!done && cycles<500) begin
                // A spurious start while busy must be ignored; feat is already changed.
                if(cycles==2) begin @(negedge clk);start=1;end
                if(cycles==3) begin @(negedge clk);start=0;end
                tick;cycles=cycles+1;
            end
            if(!done) $fatal(1,"timeout vector %0d",count);
            if(busy || scores!==expected_scores || class_id!==expected_class[1:0])
                $fatal(1,"mismatch vector %0d: got %h class %0d expected %h class %0d",count,scores,class_id,expected_scores,expected_class);
            if(cycles<min_cycles) min_cycles=cycles;
            if(cycles>max_cycles) max_cycles=cycles;
            tick;
            if(done) $fatal(1,"done lasted more than one cycle");
            if(scores!==expected_scores) $fatal(1,"score not stable after done");
            count=count+1;
        end
        $fclose(fd);
        if(count==0) $fatal(1,"zero vectors");
        $display("PASS vectors=%0d cycles_min=%0d cycles_max=%0d (start accepted to done)",count,min_cycles,max_cycles);
        $finish;
    end
endmodule
