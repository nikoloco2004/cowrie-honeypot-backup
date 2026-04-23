apt-get update
apt-get upgrade -y
systemctl status nginx
systemctl status pipeline-worker
systemctl status postgresql
cd /opt/vegabase/pipeline
python3 run.py
journalctl -u pipeline-worker -n 50
cd /var/log/nginx
tail -f error.log
systemctl restart nginx
df -h
free -m
netstat -tulpn
cd /root
cat .env
aws s3 ls s3://vegabase-prod-data
cd /opt/vegabase
git pull origin main
cd pipeline
python3 run.py
systemctl restart pipeline-worker
journalctl -u pipeline-worker -n 100
cd /root
df -h
free -m
uptime
ps aux | grep python
systemctl status postgresql
psql -U priyas -d vegabase_prod -c "SELECT COUNT(*) FROM jobs;"
cd /opt/vegabase/pipeline
python3 ingest.py
python3 run.py
cd /root
aws s3 ls s3://vegabase-prod-data/incoming/
tail -f /var/log/auth.log
cat /etc/passwd
netstat -tulpn
df -h
cd /opt/vegabase
git log --oneline
git pull origin main
cd pipeline
python3 run.py
systemctl restart pipeline-worker
journalctl -u pipeline-worker -n 100
cd /root
cat .env
aws configure list
aws s3 ls
systemctl status nginx
systemctl status pipeline-worker
systemctl status postgresql
cd /opt/vegabase/pipeline
python3 run.py
python3 ingest.py
journalctl -u pipeline-worker -n 50
cd /root
df -h
free -m
uptime
psql -U priyas -d vegabase_prod -c "SELECT COUNT(*) FROM jobs WHERE status='failed';"
psql -U priyas -d vegabase_prod -c "SELECT COUNT(*) FROM jobs WHERE status='complete';"
cd /opt/vegabase/pipeline
python3 run.py
systemctl restart pipeline-worker
cd /root
tail -f /var/log/nginx/error.log
systemctl restart nginx
df -h
free -m
cat .env
aws s3 ls s3://vegabase-prod-data
cd /opt/vegabase
git pull origin main
cd pipeline
python3 run.py
journalctl -u pipeline-worker -n 100
cd /root
uptime
df -h
free -m
systemctl status nginx
systemctl status pipeline-worker
systemctl status postgresql
cd /opt/vegabase/pipeline
python3 ingest.py
python3 run.py
cd /root
cat .env
aws s3 ls
netstat -tulpn
ps aux | grep python
df -h
free -m
