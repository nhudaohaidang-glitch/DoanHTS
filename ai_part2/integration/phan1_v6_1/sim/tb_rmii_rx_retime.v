`timescale 1ns/1ps
// Compare the retimed RX with the released V6 RX on identical RMII inputs.
// SAMPLE_NEG=0 must be cycle-identical. SAMPLE_NEG=1 must be exactly one
// positive-edge cycle later, with identical bytes, SOF/EOF and CRC results.
module tb_rmii_rx_retime;
 reg clk=0,rst_n=0,crs=0;reg[1:0] rxd=0;
 always #10 clk=~clk;
 `include "sim/rmii_rx_cases.vh"
 reg[7:0] corpus[0:TOTAL_BYTES-1];
 wire[12:0] np,nn,bp,bn;
 rmii_rx #(.SAMPLE_NEG(0)) new_pos(.ref_clk(clk),.rst_n(rst_n),.crs_dv(crs),.rxd(rxd),.o_valid(np[12]),.o_data(np[11:4]),.o_sof(np[3]),.o_eof(np[2]),.o_crc_ok(np[1]),.o_crc_err(np[0]));
 rmii_rx #(.SAMPLE_NEG(1)) new_neg(.ref_clk(clk),.rst_n(rst_n),.crs_dv(crs),.rxd(rxd),.o_valid(nn[12]),.o_data(nn[11:4]),.o_sof(nn[3]),.o_eof(nn[2]),.o_crc_ok(nn[1]),.o_crc_err(nn[0]));
 rmii_rx_v6_baseline #(.SAMPLE_NEG(0)) old_pos(.ref_clk(clk),.rst_n(rst_n),.crs_dv(crs),.rxd(rxd),.o_valid(bp[12]),.o_data(bp[11:4]),.o_sof(bp[3]),.o_eof(bp[2]),.o_crc_ok(bp[1]),.o_crc_err(bp[0]));
 rmii_rx_v6_baseline #(.SAMPLE_NEG(1)) old_neg(.ref_clk(clk),.rst_n(rst_n),.crs_dv(crs),.rxd(rxd),.o_valid(bn[12]),.o_data(bn[11:4]),.o_sof(bn[3]),.o_eof(bn[2]),.o_crc_ok(bn[1]),.o_crc_err(bn[0]));
 reg[12:0] delayed_neg;
 integer grace=0,cycles=0;
 integer byte_count[0:1],frame_count[0:1],in_frame[0:1],crc_good[0:1],crc_bad[0:1];
 integer channel;reg[12:0] q;
 always @(posedge clk) begin
  if(!rst_n)begin delayed_neg<=0;grace=0;end
  else begin delayed_neg<=bn;grace=grace+1;end
  #1;
  if(rst_n && grace>3)begin
   cycles=cycles+1;
   if(np!==bp)$fatal(1,"SAMPLE_NEG=0 changed at cycle %0d",cycles);
   if(nn!==delayed_neg)$fatal(1,"SAMPLE_NEG=1 differs from delayed baseline at cycle %0d new=%h expected=%h",cycles,nn,delayed_neg);
   for(channel=0;channel<2;channel=channel+1)begin
    q=channel ? nn : np;
    if(q[12])begin
     if(byte_count[channel]>=TOTAL_BYTES)$fatal(1,"Unexpected RX byte");
     if(q[11:4]!==corpus[byte_count[channel]])$fatal(1,"RX payload/FCS mismatch channel=%0d index=%0d",channel,byte_count[channel]);
     if(q[3] !== (in_frame[channel]==0))$fatal(1,"SOF mismatch");
     byte_count[channel]=byte_count[channel]+1;in_frame[channel]=in_frame[channel]+1;
    end
    if(q[2])begin
     if(frame_count[channel]>=CASES)$fatal(1,"Unexpected EOF");
     if(in_frame[channel]!=frame_len[frame_count[channel]])$fatal(1,"RX frame length mismatch");
     if(q[1]!==good[frame_count[channel]] || q[0]!==!good[frame_count[channel]])$fatal(1,"CRC result mismatch");
     if(q[1])crc_good[channel]=crc_good[channel]+1;else crc_bad[channel]=crc_bad[channel]+1;
     frame_count[channel]=frame_count[channel]+1;in_frame[channel]=0;
    end
   end
  end
 end
 task put_byte(input[7:0] value,input integer skew);
  integer i;begin
   for(i=0;i<4;i=i+1)begin @(posedge clk);#(skew);crs=1;rxd=value[2*i+:2];end
  end
 endtask
 integer i,j,k,offset=0;
 initial begin
  for(i=0;i<2;i=i+1)begin byte_count[i]=0;frame_count[i]=0;in_frame[i]=0;crc_good[i]=0;crc_bad[i]=0;end
  $readmemh("sim/rmii_rx_packets.hex",corpus);
  repeat(8)@(posedge clk);#2;rst_n=1;repeat(8)@(posedge clk);
  for(i=0;i<CASES;i=i+1)begin
   for(k=0;k<7;k=k+1)put_byte(8'h55,phase[i]);put_byte(8'hd5,phase[i]);
   for(j=0;j<frame_len[i];j=j+1)put_byte(corpus[offset+j],phase[i]);
   offset=offset+frame_len[i];@(posedge clk);#(phase[i]);crs=0;rxd=0;
   repeat(48)@(posedge clk); // Minimum 96-bit RMII IFG.
   if(i==CASES/2)begin #2;rst_n=0;repeat(8)@(posedge clk);#2;rst_n=1;repeat(8)@(posedge clk);end
  end
  repeat(16)@(posedge clk);#2;
  for(i=0;i<2;i=i+1)begin
   if(byte_count[i]!=TOTAL_BYTES || frame_count[i]!=CASES || crc_bad[i]!=10 || crc_good[i]!=30)$fatal(1,"RX totals mismatch");
  end
  $display("PASS V6_1_RMII_RX frames_per_edge=%0d bytes_per_edge=%0d good_crc=30 bad_crc=10 cycle_equivalence=%0d neg_latency_added=1",CASES,TOTAL_BYTES,cycles);
  $finish;
 end
 initial begin #10000000;$fatal(1,"RX timeout");end
endmodule
