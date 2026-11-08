"""Create a local V5 top project with an absolute firmware initialization path.

Does not run synthesis, place/route or program the board.
"""
import argparse
from pathlib import Path
from xml.sax.saxutils import escape

root=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--mode',choices=['mac','demo','noeth'],default='mac')
args=parser.parse_args();mode={'mac':2,'demo':1,'noeth':0}[args.mode]
folder=root/'build/gowin';folder.mkdir(parents=True,exist_ok=True)
fw=(root/'fw/firmware.hex').as_posix()
if not Path(fw).is_file():raise SystemExit('Missing compiled V5 firmware.hex')
wrapper='''module gowin_top (
 input clk_27m, input rst_n, input key_n, output uart_tx,
 inout oled_sda, inout oled_scl,
 input a_ref_clk, input a_crs_dv, input [1:0] a_rxd, output a_tx_en, output [1:0] a_txd,
 input b_ref_clk, input b_crs_dv, input [1:0] b_rxd, output b_tx_en, output [1:0] b_txd,
 output [5:0] led_n);
 tangnano9k_top #(.FIRMWARE("FIRMWARE_PATH"),.SELFTEST(MODE),.REF_METER(0)) u_top (
 .clk_27m(clk_27m),.rst_n(rst_n),.key_n(key_n),.uart_tx(uart_tx),
 .oled_sda(oled_sda),.oled_scl(oled_scl),
 .a_ref_clk(a_ref_clk),.a_crs_dv(a_crs_dv),.a_rxd(a_rxd),.a_tx_en(a_tx_en),.a_txd(a_txd),
 .b_ref_clk(b_ref_clk),.b_crs_dv(b_crs_dv),.b_rxd(b_rxd),.b_tx_en(b_tx_en),.b_txd(b_txd),.led_n(led_n));
endmodule
'''.replace('FIRMWARE_PATH',fw.replace('"','\\"')).replace('SELFTEST(MODE)','SELFTEST('+str(mode)+')')
(folder/'gowin_top.v').write_text(wrapper)
sources=[line.strip() for line in (root/'sources.f').read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')]
sources+=['rtl/board/tangnano9k_top.v','build/gowin/gowin_top.v']
files='\n'.join('        <File path="'+escape(p)+'" type="file.verilog" enable="1"/>' for p in sources)
files+='\n        <File path="board/tangnano9k.cst" type="file.cst" enable="1"/>\n        <File path="board/tangnano9k.sdc" type="file.sdc" enable="1"/>'
project='''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE gowin-fpga-project>
<Project><Template>FPGA</Template><Version>5</Version>
<Device name="GW1NR-9C" pn="GW1NR-LV9QN88PC6/I5">gw1nr9c-004</Device>
<FileList>
FILES
</FileList></Project>
'''.replace('FILES',files)
(root/'gateway_phan1_v5.gprj').write_text(project)
print('Created:',root/'gateway_phan1_v5.gprj')
print('Set top module gowin_top, then run Synthesize in Gowin. Mode:',args.mode)
print('System clock 27 MHz; RMII reference clocks 50 MHz. Full-top timing and board behavior remain unverified.')
