"""One connect/publish(QoS1)/disconnect per reading; records success and elapsed time."""
import argparse,json,time,threading,re
import paho.mqtt.client as mqtt
p=argparse.ArgumentParser();p.add_argument('--host',default='198.18.0.1');p.add_argument('--port',type=int,default=1883)
p.add_argument('--payload-bytes',type=int,default=0)
p.add_argument('--client-prefix',default='p2-sensor')
p.add_argument('--count',type=int,default=30);p.add_argument('--interval',type=float,default=1)
a=p.parse_args()
if not 0<=a.payload_bytes<=4096:p.error('payload-bytes 0..4096')
if not re.fullmatch(r'[A-Za-z0-9_-]{1,24}',a.client_prefix):p.error('client-prefix must be 1..24 letters/digits/_/-')
for i in range(a.count):
    began=time.time();ready=threading.Event();connection={'ok':False};error='';client=None;looping=False
    try:
        client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id=f'{a.client_prefix}-{i}')
        def on_connect(c,u,flags,reason,properties):
            connection['ok']=not reason.is_failure;ready.set()
        client.on_connect=on_connect
        client.connect(a.host,a.port,keepalive=10);client.loop_start();looping=True
        if not ready.wait(3) or not connection['ok']:raise TimeoutError('connect/CONNACK timeout or rejection')
        payload_data={'sensor_id':a.client_prefix,'seq':i,'sent_at':began,'temperature':28+(i%5)/10}
        if a.payload_bytes:payload_data['padding']='x'*a.payload_bytes
        payload=json.dumps(payload_data)
        info=client.publish('lab/temperature',payload,qos=1)
        info.wait_for_publish(timeout=3)
        if not info.is_published():raise TimeoutError('PUBACK timeout')
        ok=True
    except Exception as e:ok=False;error=str(e)
    finally:
        if client:
            client.disconnect()
            if looping:client.loop_stop()
    print(json.dumps({'timestamp':began,'sensor_id':a.client_prefix,'seq':i,'ok':ok,'elapsed_ms':round((time.time()-began)*1000,3),'error':error}),flush=True)
    time.sleep(max(0,a.interval-(time.time()-began)))
