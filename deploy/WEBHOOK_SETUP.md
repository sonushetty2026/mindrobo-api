# GitHub Webhook Auto-Deploy Setup

Automatic deployment triggers when code is pushed to `main`.

## Architecture

1. **GitHub webhook** → sends POST to `http://52.159.104.87:9001/deploy`
2. **webhook_server.py** → validates signature, triggers deploy
3. **deploy.sh** → pulls code, installs deps, runs migrations, restarts service
4. **systemd service** → keeps webhook server running

## Endpoints

- Webhook: `http://52.159.104.87:9001/deploy`
- Health: `http://52.159.104.87:9001/health`

## Monitoring

```bash
journalctl -u mindrobo-webhook -f
tail -f /home/azureuser/deploy.log
```
