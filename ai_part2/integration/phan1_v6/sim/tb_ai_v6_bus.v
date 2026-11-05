`timescale 1ns/1ps
// Numerical Wishbone integration, not a network detection benchmark.
module tb_ai_v6_bus;
    reg clk=0; always #5 clk=~clk;
    reg rst=1,stb=0,we=0;
    reg [31:0] adr=0,dat_w=0;
    reg [3:0] sel=15;
    wire [31:0] dat_r;wire ack,start,busy,done;
    wire [47:0] feat,scores;wire [1:0] cls;
    wb_ai_regs regs(clk,rst,stb,we,adr,sel,dat_w,dat_r,ack,start,feat,busy,done,cls,scores);
    ai_core core(clk,!rst,start,feat,busy,done,cls,scores);
    integer fd,rc,count=0,expected_class,polls,i;
    reg [47:0] x,expected_scores;reg [31:0] value;
    task wr(input [31:0] offset,input [31:0] value,input [3:0] mask);
        begin
            @(negedge clk);stb=1;we=1;adr=32'h30000000+offset;dat_w=value;sel=mask;
            @(posedge clk);#1;if(!ack)$fatal(1,"write ACK missing");
            @(negedge clk);stb=0;we=0;@(posedge clk);#1;
        end
    endtask
    task rd(input [31:0] offset,output [31:0] value);
        begin
            @(negedge clk);stb=1;we=0;adr=32'h30000000+offset;
            @(posedge clk);#1;if(!ack)$fatal(1,"read ACK missing");value=dat_r;
            @(negedge clk);stb=0;@(posedge clk);#1;
        end
    endtask
    task wait_done;
        begin
            polls=0;value=0;
            while(!value[1] && polls<100)begin rd(0,value);polls=polls+1;end
            if(!value[1] || value[0])$fatal(1,"DONE/BUSY incorrect");
        end
    endtask
    initial begin
        repeat(3)@(posedge clk);@(negedge clk);rst=0;
        // Byte enables and split 48-bit feature registers.
        wr(8,32'h12345678,15);wr(8,32'h000000ab,1);rd(8,value);
        if(value!==32'h123456ab)$fatal(1,"FEAT_LO byte enables");
        wr(12,32'hdead0123,15);wr(12,32'h00004500,2);rd(12,value);
        if(value!==32'h00004523)$fatal(1,"FEAT_HI byte enables");
        // START while busy is ignored; ABORT stops waiting without resetting core.
        wr(8,0,15);wr(12,0,15);wr(4,1,15);wr(4,1,15);wr(4,2,15);
        while(busy)begin @(posedge clk);#1;end
        rd(0,value);if(value[1])$fatal(1,"aborted operation latched stale DONE");
        fd=$fopen("sim/ai_v6_vectors.txt","r");if(!fd)$fatal(1,"missing vectors");
        while(!$feof(fd))begin
            rc=$fscanf(fd,"%h %h %d\n",x,expected_scores,expected_class);
            if(rc!=3)$fatal(1,"malformed vector");
            wr(8,x[31:0],15);wr(12,{16'b0,x[47:32]},15);wr(4,1,15);
            if(count==0)wr(4,1,15);
            wait_done;
            rd(16,value);if(value!==expected_class)$fatal(1,"class mismatch vector %0d",count);
            for(i=0;i<3;i=i+1)begin
                rd(20+4*i,value);
                if(value!=={{16{expected_scores[i*16+15]}},expected_scores[i*16+:16]})
                    $fatal(1,"signed score mismatch vector %0d score %0d",count,i);
            end
            rd(32,value);if(value!=86)$fatal(1,"wrapper LAT %0d, expected 86",value);
            rd(0,value);if(!value[1])$fatal(1,"DONE did not stay latched");
            count=count+1;
        end
        $fclose(fd);
        if(count!=3762)$fatal(1,"wrong vector count %0d",count);
        $display("PASS V6_WISHBONE vectors=%0d wrapper_cycles=86 signed_scores=OK byte_enables=OK abort=OK",count);
        $finish;
    end
    initial begin #100000000;$fatal(1,"watchdog timeout");end
endmodule
