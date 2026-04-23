cd /opt/vegabase/pipeline
python3 ingest.py
python3 run.py
psql -U priyas -d vegabase_prod
ls -la
cd ~
cat .env
aws s3 ls s3://vegabase-prod-data
aws s3 sync ./data s3://vegabase-prod-data
python3 -c "import anthropic; print(anthropic.__version__)"
pip install -r requirements.txt
cd /var/log
tail -f auth.log
sudo systemctl restart postgresql
sudo systemctl status pipeline-worker
git pull origin main
python3 run.py
psql -U priyas -d vegabase_prod -c "SELECT COUNT(*) FROM jobs WHERE status='pending';"
python3 ingest.py
cd /opt/vegabase/pipeline
python3 run.py
psql -U priyas -d vegabase_prod -c "SELECT * FROM jobs WHERE status='failed' LIMIT 10;"
python3 ingest.py
aws s3 ls s3://vegabase-prod-data/incoming/
aws s3 sync ./data s3://vegabase-prod-data
cd ~
cat .env
pip install anthropic --upgrade
python3 run.py
psql -U priyas -d vegabase_prod
cd /opt/vegabase/pipeline
ls -la
cat ingest.py
python3 ingest.py
python3 run.py
psql -U priyas -d vegabase_prod -c "SELECT COUNT(*) FROM jobs;"
aws s3 ls s3://vegabase-prod-data
cd ~
cat .env
git pull origin main
git status
cd /opt/vegabase/pipeline
python3 run.py
python3 ingest.py
psql -U priyas -d vegabase_prod -c "SELECT customer_id, COUNT(*) FROM jobs GROUP BY customer_id;"
aws s3 sync ./data s3://vegabase-prod-data
cd ~
pip install psycopg2-binary
python3 run.py
sudo systemctl restart postgresql
psql -U priyas -d vegabase_prod
cd /opt/vegabase/pipeline
python3 ingest.py
python3 run.py
psql -U priyas -d vegabase_prod -c "SELECT COUNT(*) FROM jobs WHERE status='complete';"
aws s3 ls s3://vegabase-prod-data/incoming/
aws s3 sync ./data s3://vegabase-prod-data
cd ~
cat .env
pip install -r requirements.txt
python3 run.py
cd /opt/vegabase/pipeline
python3 ingest.py
psql -U priyas -d vegabase_prod -c "SELECT * FROM jobs WHERE status='failed';"
python3 run.py
aws s3 ls s3://vegabase-prod-data
sudo systemctl status postgresql
sudo systemctl restart postgresql
psql -U priyas -d vegabase_prod
cd ~
cat .env
git pull origin main
cd /opt/vegabase/pipeline
python3 ingest.py
python3 run.py
psql -U priyas -d vegabase_prod -c "SELECT COUNT(*) FROM jobs WHERE status='pending';"
aws s3 sync ./data s3://vegabase-prod-data
python3 run.py
psql -U priyas -d vegabase_prod -c "SELECT * FROM jobs ORDER BY created_at DESC LIMIT 5;"
cd ~
cat .env
pip install anthropic --upgrade
python3 -c "import anthropic; print(anthropic.__version__)"
cd /opt/vegabase/pipeline
python3 run.py
python3 ingest.py
psql -U priyas -d vegabase_prod
aws s3 ls s3://vegabase-prod-data/incoming/
aws s3 sync ./data s3://vegabase-prod-data
sudo systemctl status pipeline-worker
sudo systemctl restart pipeline-worker
cd ~
cat .env
git status
git pull origin main
cd /opt/vegabase/pipeline
python3 ingest.py
python3 run.py
psql -U priyas -d vegabase_prod -c "SELECT COUNT(*) FROM jobs;"
