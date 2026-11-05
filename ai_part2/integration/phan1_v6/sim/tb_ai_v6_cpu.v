`timescale 1ns/1ps
// Execute the compiled RV32I firmware, including its real C packer and MMIO driver.
module tb_ai_v6_cpu;
    localparam CLK_HZ=27000000,BAUD=1350000,CPB=20;
    reg clk=0;always #5 clk=~clk;
    reg resetn=0;wire tx,trap,scl,sda;
    gateway_soc #(.CLK_HZ(CLK_HZ),.BAUD(BAUD),.FIRMWARE("fw/firmware_sim.hex"),
                  .SEC_CYCLES(27000000),.REF_METER(0)) dut(
        .clk(clk),.resetn(resetn),.uart_txd(tx),.btn_pressed(1'b0),
        .oled_scl_low(scl),.oled_sda_low(sda),.oled_scl_in(!scl),.oled_sda_in(!sda),
        .ref_clk_a(1'b0),.ref_clk_b(1'b0),.frm_valid(1'b0),.frm_data(8'd0),.frm_sof(1'b0),
        .frm_eof(1'b0),.frm_dir(1'b0),.frm_crc_ok(1'b0),.verdict_valid(),.verdict_drop(),
        .mac_crc_err(1'b0),.mac_overflow(1'b0),.trap(trap));
    integer fd,bitn,n=0,starts=0,cycles=0,k;reg [7:0] ch,line[0:255];
    reg [8*10-1:0] prefix;
    always @(posedge clk)begin
        cycles<=cycles+1;
        if(resetn && trap)$fatal(1,"CPU trap during POST");
        if(dut.a_start)starts<=starts+1;
    end
    initial begin repeat(20)@(posedge clk);@(negedge clk);resetn=1;end
    initial begin
        fd=$fopen("sim/out/v6_cpu_post_uart.log","w");if(!fd)$fatal(1,"cannot open log");
        forever begin
            @(negedge tx);repeat(CPB/2)@(posedge clk);
            if(!tx)begin
                for(bitn=0;bitn<8;bitn=bitn+1)begin repeat(CPB)@(posedge clk);ch[bitn]=tx;end
                repeat(CPB)@(posedge clk);$fwrite(fd,"%c",ch);
                if(ch==10)begin
                    $fflush(fd);prefix=0;
                    for(k=0;k<10;k=k+1)prefix={prefix[71:0],line[k]};
                    if(prefix=="# POST LOI")$fatal(1,"CPU POST reported failure");
                    if(n>=9 && line[0]=="#" && line[2]=="P" && line[7]=="O" && line[8]=="K")begin
                        if(starts!=36)$fatal(1,"expected 36 hardware calls and one skipped empty, got %0d",starts);
                        $display("PASS V6_RV32I_POST counters=37 inference_calls=%0d empty_skipped=1 CPU_cycles=%0d",starts,cycles);
                        $fclose(fd);$finish;
                    end
                    n=0;
                end else if(ch!=13 && n<256)begin line[n]=ch;n=n+1;end
            end
        end
    end
    initial begin repeat(1500000)@(posedge clk);$fatal(1,"CPU POST watchdog");end
endmodule
