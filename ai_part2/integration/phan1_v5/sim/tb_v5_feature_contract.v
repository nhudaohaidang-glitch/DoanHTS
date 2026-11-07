`timescale 1ns/1ps
// Header-level checks of Person 1's reference feat_core. Not validation of official Part 3.
module tb_v5_feature_contract;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,valid=0,dir=0,ipv4=1,frag=0,l4=1;
    reg [31:0] src=1,dst=32'hc0a80a02;
    reg [7:0] proto=6,flags=2;
    reg [15:0] len=40,sport=12345,dport=80;
    wire win;wire [15:0] win_id,ns,nd,np,err;wire [31:0] packets,bytes,syn,suspect,confirm;
    feat_core #(.WINDOW_CYCLES(30000)) dut(clk,rst_n,1'b1,32'hc0a80a02,32'hffffffff,
      valid,dir,ipv4,frag,l4,src,dst,proto,len,sport,dport,flags,
      win,win_id,packets,bytes,syn,ns,nd,np,err,suspect,confirm);
    integer count=0,i;
    task send(input [31:0] s,input [15:0] p,input [15:0] n,input [7:0] pr,input [7:0] f,input v4,input outbound,input fragmented,input ports_valid);
      begin
        @(negedge clk);src=s;dport=p;len=n;proto=pr;flags=f;ipv4=v4;dir=outbound;frag=fragmented;l4=ports_valid;valid=1;
        @(negedge clk);valid=0;repeat(160)@(negedge clk);
      end
    endtask
    task check(input [31:0] n,input [31:0] b,input [31:0] s,input [15:0] a,input [15:0] p,input [15:0] e);
      begin
        @(posedge win);#1;
        if(packets!==n || bytes!==b || syn!==s || ns!==a || nd!==(n?16'd1:16'd0) || np!==p || err!==e)
          $fatal(1,"feature window %0d got %0d,%0d,%0d,%0d,%0d,%0d err=%0d",count,packets,bytes,syn,ns,nd,np,err);
        count=count+1;
      end
    endtask
    initial begin
      repeat(3)@(posedge clk);@(negedge clk);rst_n=1;
      send(1,80,52,6,16,1,0,0,1);send(1,80,40,6,2,1,0,0,1);send(1,443,40,6,18,1,0,0,1);
      send(2,80,40,6,2,0,0,0,0);send(2,80,40,6,2,1,1,0,1);send(2,80,40,6,2,1,0,1,1);
      @(negedge clk);dst=32'hc0a80aff;send(3,80,40,6,2,1,0,0,1);@(negedge clk);dst=32'hc0a80a02;
      check(3,132,1,1,2,1);
      for(i=0;i<6;i=i+1)send(1,1000+i,40,6,2,1,0,0,1);
      check(6,240,6,1,6,0);
      send(20,53,28,17,0,1,0,0,1);send(21,53,28,17,0,1,0,0,1);send(20,0,84,1,0,1,0,0,0);
      check(3,140,0,2,1,0);
      check(0,0,0,0,0,0);
      for(i=0;i<130;i=i+1)send(1,2000+i,40,6,2,1,0,0,1);
      check(130,5200,130,1,128,0);
      $display("PASS V5_FEATURE_CONTRACT windows=%0d exact_to_128_and_q127_saturation=OK",count);$finish;
    end
    initial begin #3000000;$fatal(1,"feature watchdog");end
endmodule
