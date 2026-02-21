# Deployment

## systemd service

```bash
# Copy the unit file
sudo cp deploy/mindrobo-api.service /etc/systemd/system/

# Reload systemd, enable and start
sudo systemctl daemon-reload
sudo systemctl enable mindrobo-api
sudo systemctl start mindrobo-api

# Check status
sudo systemctl status mindrobo-api

# View logs
journalctl -u mindrobo-api -f
```

## Prerequisites

- Python venv at `/home/azureuser/mindrobo-api/.venv` with deps installed
- Env vars in `/home/azureuser/secrets/db.env` (DATABASE_URL, TWILIO_*, RETELL_API_KEY, etc.)
- Port 8000 open in Azure NSG / firewall
