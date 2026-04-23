sudo su
systemctl status nginx
systemctl status pipeline-worker
journalctl -u pipeline-worker -n 50
cd /opt/vegabase/pipeline
ls -la
cat run.py
sudo systemctl restart pipeline-worker
cd /var/log/nginx
tail -f error.log
tail -f access.log
sudo systemctl restart nginx
cd ~
ls -la
cat .env
git status
git log --oneline
cd /opt/vegabase
ls
cd pipeline
python3 run.py
sudo systemctl status postgresql
cd /home/priyas
ls -la
cd ~
ssh priyas@10.0.1.12
sudo tail -f /var/log/auth.log
ps aux | grep python
ps aux | grep nginx
df -h
free -m
uptime
sudo systemctl restart pipeline-worker
journalctl -u pipeline-worker -n 100
cd /opt/vegabase/pipeline
cat ingest.py
python3 run.py
sudo su
cat /etc/passwd
cat /etc/shadow
cd ~
cat .env
sudo systemctl status nginx
tail -f /var/log/nginx/error.log
sudo systemctl restart nginx
cd /opt/vegabase/pipeline
ls -la
git status
git pull origin main
python3 run.py
sudo systemctl restart pipeline-worker
journalctl -u pipeline-worker -n 200
df -h
free -m
uptime
sudo reboot
systemctl status nginx
systemctl status pipeline-worker
cd /opt/vegabase/pipeline
python3 run.py
tail -f /var/log/nginx/access.log
sudo systemctl restart nginx
cd ~
cat .env
ls -la
sudo su
journalctl -u pipeline-worker -n 50
systemctl restart pipeline-worker
cd /home/priyas
ls -la
cd ~
ssh priyas@10.0.1.12
ps aux | grep python
df -h
free -m
cat /var/log/auth.log
sudo systemctl status postgresql
cd /opt/vegabase/pipeline
python3 run.py
sudo systemctl restart pipeline-worker
journalctl -u pipeline-worker -n 100
cd ~
cat .env
git log --oneline
git status
sudo su
systemctl status nginx
systemctl status pipeline-worker
tail -f /var/log/nginx/error.log
sudo systemctl restart nginx
cd /opt/vegabase/pipeline
python3 run.py
ls -la
cat run.py
sudo systemctl restart pipeline-worker
journalctl -u pipeline-worker -n 200
cd ~
free -m
df -h
uptime
cat .env
sudo su
systemctl restart postgresql
systemctl restart pipeline-worker
systemctl restart nginx
cd /opt/vegabase/pipeline
python3 run.py
tail -f /var/log/nginx/access.log
cd ~
ls -la
cat .env
