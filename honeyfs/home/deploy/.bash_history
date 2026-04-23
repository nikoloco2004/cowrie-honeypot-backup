cd /opt/vegabase
git pull origin main
sudo systemctl restart pipeline-worker
sudo systemctl restart nginx
sudo systemctl status pipeline-worker
sudo systemctl status nginx
cd /opt/vegabase/pipeline
git pull origin main
sudo systemctl restart pipeline-worker
systemctl status nginx
systemctl status pipeline-worker
cd /opt/vegabase
git log --oneline
git pull origin main
sudo systemctl restart nginx
sudo systemctl restart pipeline-worker
cd ~
ls
git pull origin main
sudo systemctl restart pipeline-worker
sudo systemctl status pipeline-worker
