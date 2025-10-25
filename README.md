# Blue/Green Deployment with Nginx Auto-Failover

This project implements a Blue/Green deployment strategy using Nginx as a reverse proxy with automatic failover capabilities.

## Architecture

- **Blue Service**: Primary application instance (Port 8081)
- **Green Service**: Backup application instance (Port 8082)
- **Nginx**: Reverse proxy with health-based routing (Port 8080)

## Features

- Zero-downtime deployments
- Automatic failover on service failure
- Health-based traffic routing
- Manual toggle between Blue/Green
- Header forwarding (X-App-Pool, X-Release-Id)
- Configurable via environment variables

## Prerequisites

- Docker Engine 20.10+
- Docker Compose V2+
- Linux/Unix environment

## Quick Start

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd blue_green_deployment
```

### 2. Configure Environment Variables
```bash
cp .env.example .env
```

Edit `.env` if needed to customize:
- Image references
- Active pool (blue/green)
- Release identifiers

### 3. Start Services
```bash
docker compose up -d
```

### 4. Verify Deployment
```bash
# Check all containers are running
docker compose ps

# Test the main endpoint (through Nginx)
curl -i http://localhost:8080/version

# Test Blue directly
curl -i http://localhost:8081/version

# Test Green directly
curl -i http://localhost:8082/version
```

## Testing Failover

### Automatic Failover Test

1. **Trigger failure on Blue**:
```bash
curl -X POST "http://localhost:8081/chaos/start?mode=error"
```

2. **Verify automatic switch to Green**:
```bash
curl -i http://localhost:8080/version
```

Expected: Response shows `X-App-Pool: green`

3. **Test stability (zero failed requests)**:
```bash
for i in {1..20}; do
  curl -s -o /dev/null -w "Request $i: %{http_code}\n" http://localhost:8080/version
  sleep 0.5
done
```

Expected: All requests return `200`

4. **Stop chaos**:
```bash
curl -X POST "http://localhost:8081/chaos/stop"
```

### Manual Toggle Test

1. **Edit `.env` to switch active pool**:
```bash
nano .env

## Endpoints

### Main Service (Nginx Proxy)
- `http://localhost:8080/version` - Get application version
- `http://localhost:8080/healthz` - Health check

### Direct Access
- `http://localhost:8081/*` - Blue instance
- `http://localhost:8082/*` - Green instance

### Chaos Engineering
- `POST http://localhost:8081/chaos/start?mode=error` - Trigger errors on Blue
- `POST http://localhost:8081/chaos/stop` - Stop chaos on Blue
- `POST http://localhost:8082/chaos/start?mode=error` - Trigger errors on Green
- `POST http://localhost:8082/chaos/stop` - Stop chaos on Green

## Configuration

### Nginx Failover Settings

- **Max Fails**: 1 (marks server down after 1 failure)
- **Fail Timeout**: 10s (server marked down for 10 seconds)
- **Connection Timeout**: 2s
- **Read Timeout**: 2s
- **Retry Conditions**: error, timeout, http_500, http_502, http_503, http_504

## Troubleshooting

### Containers not starting
```bash
docker compose logs
docker compose down
docker compose up -d
```

### Port conflicts
```bash
# Check what's using ports
sudo lsof -i :8080
sudo lsof -i :8081
sudo lsof -i :8082

# Or change ports in docker-compose.yml
```

### Nginx not routing correctly
```bash
# Check generated Nginx config
docker compose exec nginx cat /etc/nginx/nginx.conf

# Check Nginx logs
docker compose logs nginx
```

### Application not responding
```bash
# Check app logs
docker compose logs app_blue
docker compose logs app_green

# Restart specific service
docker compose restart app_blue
```

## Stopping Services
```bash
# Stop all services
docker compose down

# Stop and remove volumes
docker compose down -v
```

## Project Structure
```
.
├── docker-compose.yml          # Docker Compose configuration
├── .env                        # Environment variables (not in repo)
├── .env.example               # Example environment variables
├── nginx.conf.template        # Nginx configuration template
├── entrypoint.sh             # Nginx entrypoint script
├── failed_over.sh            # This file performs mutliple 
├── .gitignore                # This file ignores large files and sensitive files
├── README.md                 # Verifies if any failure occurs over 10 consecutive runs of the system
└── DECISION.md              # Implementation decisions
```

## Requirements Met

- Docker Compose orchestration
- Nginx reverse proxy with upstream configuration
- Primary/backup failover mechanism
- Automatic retry on failure
- Zero failed requests during failover
- Header forwarding (X-App-Pool, X-Release-Id)
- Environment-based configuration
- Direct access to Blue/Green for chaos testing
- Health-based routing with tight timeouts
