"""One connect/publish(QoS1)/disconnect per reading; records success and elapsed time."""
import argparse,json,time,threading
import paho.mqtt.client as mqtt
p=argparse.ArgumentParser();p.add_argument('--host',default='198.18.0.1');p.add_argument('--port',type=int,default=1883)
p.add_argument('--count',type=int,default=30);p.add_argument('--interval',type=float,default=1)
a=p.parse_args()
for i in range(a.count):
    began=time.time();ready=threading.Event();connection={'ok':False};error='';client=None;looping=False
    try:
        client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id=f'p2-sensor-{i}')
        def on_connect(c,u,flags,reason,properties):
            connection['ok']=not reason.is_failure;ready.set()
        client.on_connect=on_connect
        client.connect(a.host,a.port,keepalive=10);client.loop_start();looping=True
        if not ready.wait(3) or not connection['ok']:raise TimeoutError('connect/CONNACK timeout or rejection')
        payload=json.dumps({'seq':i,'sent_at':began,'temperature':28+(i%5)/10})
        info=client.publish('lab/temperature',payload,qos=1)
        info.wait_for_publish(timeout=3)
        if not info.is_published():raise TimeoutError('PUBACK timeout')
        ok=True
    except Exception as e:ok=False;error=str(e)
    finally:
        if client:
            client.disconnect()
            if looping:client.loop_stop()
    print(json.dumps({'timestamp':began,'seq':i,'ok':ok,'elapsed_ms':round((time.time()-began)*1000,3),'error':error}),flush=True)
    time.sleep(max(0,a.interval-(time.time()-began)))
