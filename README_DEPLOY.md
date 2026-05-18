# Deploy rápido – Leviathan Edge Core (motor persistente)

## Requisitos
- Python 3.10+
- pip install -r streamlit_app/requirements.txt

## Arranque rápido (local)
1. cd streamlit_app
2. python engine_runner.py &   # motor en segundo plano
3. streamlit run app.py        # UI en http://localhost:8501

## Con pm2 (recomendado para VPS)
pm2 start engine_runner.py --name leviathan --cwd streamlit_app/
pm2 save
pm2 startup

## Con systemd
Crear /etc/systemd/system/leviathan.service con el contenido:
[Unit]
Description=Leviathan Edge Engine
After=network.target

[Service]
Type=simple
User=tu-usuario
WorkingDirectory=/ruta/a/streamlit_app
ExecStart=/usr/bin/python3 engine_runner.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

sudo systemctl enable leviathan
sudo systemctl start leviathan

## Con nohup (más simple)
cd streamlit_app
nohup python engine_runner.py > ../logs/engine.log 2>&1 &
echo $! > runtime/engine.pid

## Para detener
- Desde Streamlit: botón STOP
- Manual: kill $(cat runtime/engine.pid)
- pm2: pm2 stop leviathan
- systemd: sudo systemctl stop leviathan

## Monitoreo
- Streamlit UI muestra estado en tiempo real
- Revisar runtime/logs.txt
- tail -f logs/engine.log
