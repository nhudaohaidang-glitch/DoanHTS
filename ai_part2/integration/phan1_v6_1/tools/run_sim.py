"""Run Person 1's tests and V6 integration tests with explicit failure status."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def run(name):
    if not shutil.which('iverilog') or not shutil.which('vvp'):
        raise ValueError('Need Icarus Verilog (iverilog and vvp) in PATH')
    out=ROOT/'sim/out';out.mkdir(parents=True,exist_ok=True)
    if name in ('demo_post','demo'):
        prep=subprocess.run([sys.executable,str(ROOT/'CHUAN_BI_DEMO_GOWIN.py')],cwd=ROOT,capture_output=True,text=True)
        if prep.returncode:raise ValueError(prep.stdout+prep.stderr)
    tests={
      'demo_post':('tb_board_demo_v6_1',['-c','sources.f','rtl/board/tangnano9k_top.v','build/gowin_demo/gowin_demo_top.v','sim/tb_board_demo_v6_1.v','-Ptb_board_demo_v6_1.FAST=0'],'PASS V6_1_BOARD_DEMO_POST',180),
      'demo':('tb_board_demo_v6_1',['-c','sources.f','rtl/board/tangnano9k_top.v','build/gowin_demo/gowin_demo_top.v','sim/tb_board_demo_v6_1.v'],'PASS V6_1_BOARD_DEMO_ALL3',600),
      'rmii_rx':('tb_rmii_rx_retime',['rtl/part4_eth/rmii_rx.v','sim/rmii_rx_v6_baseline.v','sim/tb_rmii_rx_retime.v'],'PASS V6_1_RMII_RX',60),
      'ai_v6':('tb_ai_v6_bus',['rtl/wb_ai_regs.v','rtl/part2_ai/ai_core_model_v6.v','sim/tb_ai_v6_bus.v'],'PASS V6_WISHBONE',60),
      'ai_cpu':('tb_ai_v6_cpu',['-c','sources.f','sim/tb_ai_v6_cpu.v'],'PASS V6_RV32I_POST',180),
      'features':('tb_v6_feature_contract',['rtl/stubs/feat_core_stub.v','sim/tb_v6_feature_contract.v'],'PASS V6_FEATURE_CONTRACT',60),
      'full':('tb_gateway',['-c','sources.f','sim/tb_gateway.v'],'[tb] PASS',600),
      'quick':('tb_gateway',['-c','sources.f','sim/tb_gateway.v'],None,180),
      'vcd':('tb_gateway',['-c','sources.f','sim/tb_gateway.v'],'[tb] PASS',600),
      'mac':('tb_eth_mac',['rtl/part4_eth/async_fifo.v','rtl/part4_eth/rmii_rx.v','rtl/part4_eth/rmii_tx.v','rtl/part4_eth/eth_mac.v','sim/tb_eth_mac.v'],'[tb] PASS',180),
      'system':('tb_system_mac',['-c','sources.f','rtl/board/tangnano9k_top.v','sim/tb_system_mac.v'],'[tb] PASS',600),
      'board':('tb_board',['-c','sources.f','rtl/board/tangnano9k_top.v','sim/ssd1306_model.v','sim/tb_board.v'],'[tb] PASS',600),
      'oled':('tb_oled',['-c','sources.f','sim/ssd1306_model.v','sim/tb_oled.v'],'[tb] PASS',600)}
    top,files,marker,timeout=tests[name];exe=out/(name+'.vvp')
    print('Compile/run:',name,'(network scenarios may take several minutes)',flush=True)
    compile=subprocess.run(['iverilog','-g2012','-s',top,'-o',str(exe),*files],cwd=ROOT,capture_output=True,text=True)
    (out/(name+'_compile.log')).write_text(compile.stdout+compile.stderr)
    if compile.returncode:raise ValueError(compile.stdout+compile.stderr)
    args=['vvp','-n',str(exe)]+(['+stop=9'] if name=='quick' else ['+vcd'] if name=='vcd' else [])
    result=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,timeout=timeout)
    log=result.stdout+result.stderr;(out/(name+'_result.log')).write_text(log);print(log,flush=True)
    failed=result.returncode!=0 or any(x in log for x in ('[tb] FAIL','[tb] HET GIO','FATAL:')) or (marker is not None and marker not in log)
    checks=[]
    if name in ('full','vcd'):
        p=subprocess.run([sys.executable,'tools/check_log.py','sim/out/uart.log'],cwd=ROOT,capture_output=True,text=True)
        checks.append(dict(kind='uart_policy_scenario',passed=p.returncode==0));print(p.stdout+p.stderr)
        (out/(name+'_uart_check.log')).write_text(p.stdout+p.stderr);failed|=p.returncode!=0
    report=dict(test=name,passed=not failed,full_check=marker is not None,extra_checks=checks,
                note='Arithmetic tests are not detection accuracy; full/system failures remain visible.')
    (out/(name+'_status.json')).write_text(json.dumps(report,indent=2)+'\n')
    if failed:raise ValueError('Test failed: '+name+'; see sim/out/'+name+'_result.log')
    if marker is None:print('Quick trace finished; no full scenario PASS claimed.')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('test',nargs='?',default='full',choices=['demo_post','demo','rmii_rx','ai_v6','ai_cpu','features','full','quick','vcd','mac','system','board','oled','all'])
    args=parser.parse_args()
    try:
        for name in (['ai_v6','ai_cpu','features','rmii_rx','full','oled','board','mac','system'] if args.test=='all' else [args.test]):run(name)
    except (ValueError,OSError,subprocess.TimeoutExpired) as error:parser.exit(1,'ERROR: '+str(error)+'\n')
