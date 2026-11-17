import os
import datetime
import logging
import hashlib
from typing import List, Dict, Any, Optional
import httpx
from app.services.github.base import BaseGitHubClient
from app.core.security import normalize_repo_name
from app.core.config import settings

logger = logging.getLogger(__name__)

MOCK_REPOSITORIES = {
    "reposage-demo/ecommerce-api": {
        "id": 1001,
        "full_name": "reposage-demo/ecommerce-api",
        "owner": "reposage-demo",
        "name": "ecommerce-api",
        "default_branch": "main",
        "is_private": False,
        "is_demo": True,
        "commit_sha": "7b9f8e4a1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f",
        "summary": "E-Commerce backend API with order processing, Stripe payment service, and JWT authentication.",
        "files": {
            "services/payment.py": '''"""Payment Processing Service."""
import hashlib
import hmac
import time
from typing import Optional, Dict, Any
from auth.jwt import verify_access_token
from models.user import User, Payment

class PaymentGatewayError(Exception):
    pass

class PaymentService:
    def __init__(self, api_key: str, gateway_url: str):
        self.api_key = api_key
        self.gateway_url = gateway_url

    def create_charge(self, user: User, amount_cents: int, currency: str = "USD") -> Dict[str, Any]:
        """Creates a charge via payment gateway."""
        if amount_cents <= 0:
            raise ValueError("Amount must be greater than zero")
        
        # Simulating external gateway charge
        charge_id = f"ch_{int(time.time())}"
        return {
            "charge_id": charge_id,
            "status": "succeeded",
            "amount": amount_cents,
            "currency": currency,
            "user_id": user.id
        }

    def execute_raw_user_query(self, user_id: str, db_session: Any) -> Any:
        """Finds transactions for user (Note: Demonstration helper)."""
        # Insecure query demo:
        query = f"SELECT * FROM payments WHERE user_id = '{user_id}'"
        return db_session.execute(query)

    def verify_webhook_signature(self, payload: bytes, header_signature: str, webhook_secret: str) -> bool:
        """Verifies HMAC signature on incoming payment gateway webhooks."""
        computed = hmac.new(webhook_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, header_signature)
''',
            "api/orders.py": '''"""Order Management API Endpoints."""
import datetime
from typing import List, Dict, Any
from auth.jwt import verify_access_token
from services.payment import PaymentService
from models.user import User, Order

class OrderManager:
    def __init__(self, payment_service: PaymentService):
        self.payment_service = payment_service

    def create_order(self, user: User, items: List[Dict[str, Any]]) -> Order:
        """Calculates order total and charges the customer."""
        total_cents = sum(item.get("price_cents", 0) * item.get("quantity", 1) for item in items)
        charge = self.payment_service.create_charge(user, total_cents)
        
        return Order(
            id=101,
            user_id=user.id,
            total_cents=total_cents,
            status="paid" if charge["status"] == "succeeded" else "failed"
        )

    def calculate_cart_total(self, items: List[Dict[str, Any]], tax_rate: float = 0.08) -> int:
        """Calculates subtotal and taxes."""
        subtotal = sum(i["price_cents"] * i.get("quantity", 1) for i in items)
        tax = int(subtotal * tax_rate)
        return subtotal + tax
''',
            "auth/jwt.py": '''"""JWT Authentication and Token Management."""
import datetime
from typing import Optional, Dict, Any

SECRET_KEY = "demo-mock-jwt-secret-do-not-use-in-production"
ALGORITHM = "HS256"

def generate_access_token(user_id: int, expires_delta: Optional[datetime.timedelta] = None) -> str:
    """Creates a JWT access token for authentication."""
    expire = datetime.datetime.utcnow() + (expires_delta or datetime.timedelta(hours=1))
    payload = {"sub": str(user_id), "exp": expire}
    return f"mock-token-{user_id}-{int(expire.timestamp())}"

def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Validates the JWT access token signature and expiration."""
    if not token or not token.startswith("mock-token-"):
        return None
    parts = token.split("-")
    if len(parts) >= 3:
        user_id = int(parts[2])
        return {"sub": str(user_id)}
    return None
''',
            "models/user.py": '''"""Data models for Users, Orders, and Payments."""
from dataclasses import dataclass
from typing import Optional

@dataclass
class User:
    id: int
    email: str
    is_active: bool = True

@dataclass
class Order:
    id: int
    user_id: int
    total_cents: int
    status: str

@dataclass
class Payment:
    id: int
    order_id: int
    amount_cents: int
    status: str
''',
            "README.md": '''# E-Commerce Microservice

RepoSage Sample Demonstration Repository.
Features:
- Payment integration with Stripe gateway (`services/payment.py`)
- Order workflow management (`api/orders.py`)
- Authentication token lifecycle (`auth/jwt.py`)
''',
            "Dockerfile": '''FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "-m", "api.orders"]
''',
            "Makefile": '''.PHONY: test lint

test:
\tpytest tests/

lint:
\tflake8 .
''',
            "scripts/deploy.sh": '''#!/bin/bash
set -e
echo "Starting deployment of ecommerce-api..."
python -m api.orders
''',
            ".env": "STRIPE_SECRET_KEY=sk_live_mock_super_secret_stripe_token_xyz987\\nDATABASE_PASSWORD=SuperSecretPass123!\\n",
            "assets/logo.png": "\\x89PNG\\r\\n\\x1a\\n\\x00\\x00\\x00\\rIHDR\\x00\\x00\\x00\\x10\\x00\\x00\\x00\\x10\\x08\\x06\\x00\\x00\\x00",
            "node_modules/stripe/index.js": "module.exports = { Stripe: function() {} };\\n"
        },
        "pull_requests": {
            101: {
                "number": 101,
                "title": "feat: Add payment retry & gateway webhook support",
                "base_sha": "7b9f8e4a1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f",
                "head_sha": "9c8b7a6f5e4d3c2b1a0f9e8d7c6b5a4f3e2d1c0b",
                "diff": """diff --git a/services/payment.py b/services/payment.py
index 1a2b3c4..5d6e7f8 100644
--- a/services/payment.py
+++ b/services/payment.py
@@ -40,10 +40,22 @@ class PaymentService:
     def execute_raw_user_query(self, user_id: str, db_session: Any) -> Any:
         \"\"\"Finds transactions for user (Note: Demonstration helper).\"\"\"
-        query = f"SELECT * FROM payments WHERE user_id = '{user_id}'"
+        # High severity issue: raw SQL query without parameterized bind variables
+        query = f"SELECT id, amount, status FROM payments WHERE user_id = '{user_id}' AND is_active = 1"
         return db_session.execute(query)
 
+    def call_stripe_gateway(self, payload: dict) -> dict:
+        \"\"\"Calls external Stripe endpoint.\"\"\"
+        # Medium severity issue: missing timeout handling on external HTTP call
+        import httpx
+        response = httpx.post("https://api.stripe.com/v1/charges", json=payload)
+        return response.json()
+
     def verify_webhook_signature(self, payload: bytes, header_signature: str, webhook_secret: str) -> bool:
         \"\"\"Verifies HMAC signature on incoming payment gateway webhooks.\"\"\"
"""
            }
        }
    },
    "reposage-demo/task-manager-api": {
        "id": 1002,
        "full_name": "reposage-demo/task-manager-api",
        "owner": "reposage-demo",
        "name": "task-manager-api",
        "default_branch": "main",
        "is_private": False,
        "is_demo": True,
        "commit_sha": "commit_task_main_11111",
        "summary": "FastAPI task management service with SQLite persistence and project tracking.",
        "files": {
            "requirements.txt": """fastapi==0.110.0
uvicorn==0.28.0
sqlalchemy==2.0.28
pydantic==2.6.4
pytest==8.1.1
""",
            "main.py": '''"""Task Manager Service Entry Point."""
from fastapi import FastAPI
from routers.tasks import router as task_router
from database import init_db

app = FastAPI(title="Task Manager API", version="1.0.0")

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "task-manager-api"}

app.include_router(task_router, prefix="/api/v1/tasks")
''',
            "database.py": '''"""SQLite Database Engine Configuration."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./tasks.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    Base.metadata.create_all(bind=engine)
''',
            "models/task.py": '''"""Data models for Projects and Tasks."""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    tasks = relationship("Task", back_populates="project")

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    status = Column(String(30), default="todo")
    is_completed = Column(Boolean, default=False)
    project_id = Column(Integer, ForeignKey("projects.id"))
    project = relationship("Project", back_populates="tasks")
''',
            "routers/tasks.py": '''"""Task Management REST Endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models.task import Task

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/")
def list_tasks(db: Session = Depends(get_db)):
    """Returns all team tasks."""
    return db.query(Task).all()

@router.post("/")
def create_task(title: str, project_id: int, db: Session = Depends(get_db)):
    """Creates a new team task."""
    task = Task(title=title, project_id=project_id, status="todo")
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

@router.put("/{task_id}/complete")
def complete_task(task_id: int, db: Session = Depends(get_db)):
    """Marks task as completed."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.is_completed = True
    task.status = "done"
    db.commit()
    return task
''',
            "tests/test_tasks.py": '''"""Unit tests for task endpoints."""
import pytest
from models.task import Task

def test_task_creation():
    t = Task(title="Deploy Release", project_id=1, status="todo")
    assert t.title == "Deploy Release"
    assert t.status == "todo"
    assert t.is_completed is False
''',
            "README.md": '''# Distributed Cassandra ML Analytics Pipeline
Real-time deep learning feature store backed by Apache Cassandra cluster and PyTorch distributed training nodes.
Features:
- Cassandra ring storage
- PyTorch distributed workers
'''
        },
        "branches": {
            "main": {
                "commit_sha": "commit_task_main_11111"
            },
            "develop": {
                "commit_sha": "commit_task_dev_22222",
                "extra_files": {
                    "services/notification.py": '''"""Notification alerts service for task completion."""
def send_task_completed_alert(task_id: int, recipient_email: str):
    """Sends notification email upon task completion."""
    return {"status": "sent", "task_id": task_id, "recipient": recipient_email}
'''
                }
            }
        },
        "pull_requests": {}
    },
    "reposage-demo/inventory-service": {
        "id": 1003,
        "full_name": "reposage-demo/inventory-service",
        "owner": "reposage-demo",
        "name": "inventory-service",
        "default_branch": "main",
        "is_private": False,
        "is_demo": True,
        "commit_sha": "commit_inv_main_33333",
        "summary": "Node.js TypeScript inventory warehouse service with Redis caching and SKU stock management.",
        "files": {
            "package.json": """{
  "name": "inventory-service",
  "version": "1.0.0",
  "scripts": {
    "start": "ts-node src/index.ts",
    "test": "jest",
    "build": "tsc"
  },
  "dependencies": {
    "express": "^4.19.2",
    "ioredis": "^5.3.2"
  },
  "devDependencies": {
    "typescript": "^5.4.3",
    "jest": "^29.7.0"
  }
}
""",
            "src/index.ts": '''import express from 'express';
import { WarehouseService } from './services/warehouse';

const app = express();
const port = 3000;
const warehouse = new WarehouseService();

app.use(express.json());

app.get('/health', (req, res) => {
  res.json({ status: 'healthy', service: 'inventory-service' });
});

app.get('/stock/:sku', async (req, res) => {
  const stock = await warehouse.getStock(req.params.sku);
  res.json({ sku: req.params.sku, stock });
});

app.post('/stock/:sku/replenish', async (req, res) => {
  const { quantity } = req.body;
  const updated = await warehouse.replenish(req.params.sku, quantity);
  res.json({ sku: req.params.sku, current_stock: updated });
});

app.listen(port, () => {
  console.log(`Inventory service listening on port ${port}`);
});
''',
            "src/services/warehouse.ts": '''import Redis from 'ioredis';

export class WarehouseService {
  private redis: Redis;

  constructor() {
    this.redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');
  }

  async getStock(sku: string): Promise<number> {
    const val = await this.redis.get(`sku:${sku}`);
    return val ? parseInt(val, 10) : 0;
  }

  async replenish(sku: string, count: number): Promise<number> {
    const newCount = await this.redis.incrby(`sku:${sku}`, count);
    return newCount;
  }
}
''',
            "src/models/item.ts": '''export interface InventoryItem {
  id: string;
  sku: string;
  name: string;
  warehouseLocation: string;
  reorderThreshold: number;
}
''',
            "tests/inventory.spec.ts": '''describe("WarehouseService", () => {
  it("should calculate reorder thresholds properly", () => {
    const threshold = 15;
    const currentStock = 10;
    expect(currentStock < threshold).toBe(true);
  });
});
''',
            "README.md": '''# Warehouse Inventory Microservice
Real-time stock tracking service written in TypeScript with Express and Redis caching.
Commands:
- Run: `npm start`
- Test: `npm test`
- Build: `npm run build`
'''
        },
        "pull_requests": {}
    },
    "reposage-demo/polyglot-platform": {
        "id": 1004,
        "full_name": "reposage-demo/polyglot-platform",
        "owner": "reposage-demo",
        "name": "polyglot-platform",
        "default_branch": "main",
        "is_private": False,
        "is_demo": True,
        "commit_sha": "d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9",
        "summary": "Polyglot microservices platform with Rust, Go, Java, C#, Solidity, Bash, SQL, and YAML configurations.",
        "files": {
            "src/main.rs": '''// Rust worker service
use std::collections::HashMap;

pub struct TaskEngine {
    pub workers: usize,
}

impl TaskEngine {
    pub fn new(workers: usize) -> Self {
        TaskEngine { workers }
    }

    pub fn execute_job(&self, job_id: &str) -> bool {
        println!("Executing job {}", job_id);
        true
    }
}
''',
            "src/server.go": '''package main

import "fmt"

type Dispatcher struct {
    MaxQueue int
}

func (d *Dispatcher) StartWorkerPool() error {
    fmt.Println("Worker pool active")
    return nil
}

func main() {
    d := &Dispatcher{MaxQueue: 100}
    d.StartWorkerPool()
}
''',
            "src/Application.java": '''package com.reposage.demo;

public class Application {
    private String clusterId;

    public Application(String clusterId) {
        this.clusterId = clusterId;
    }

    public void initializeCluster() {
        System.out.println("Cluster initialized: " + clusterId);
    }
}
''',
            "src/Calculator.cs": '''namespace RepoSage.Core;

public class Calculator {
    public int ComputeTax(int amount, double rate) {
        return (int)(amount * rate);
    }
}
''',
            "src/Token.sol": '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract PolyglotToken {
    string public name = "PolyglotToken";
    uint256 public totalSupply = 1000000;
}
''',
            "src/View.vue": '''<template>
  <div class="panel"><h1>{{ title }}</h1></div>
</template>
<script>
export default {
  data() { return { title: "Polyglot Dashboard" }; }
};
</script>
''',
            "src/Widget.svelte": '''<script>
  export let count = 0;
</script>
<button on:click={() => count++}>Count: {count}</button>
''',
            "scripts/deploy.sh": '''#!/bin/bash
set -euo pipefail
echo "Deploying polyglot services..."
''',
            "scripts/setup.ps1": '''# PowerShell deployment script
Write-Host "Initializing cloud instances..."
''',
            "database/schema.sql": '''CREATE TABLE IF NOT EXISTS platform_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(64) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
''',
            "config/services.yaml": '''version: "3.8"
services:
  gateway:
    image: nginx:alpine
    ports:
      - "80:80"
''',
            "config/runtime.toml": '''[runtime]
engine = "tokio"
threads = 4
''',
            "data/registry.json": '''{
  "service": "polyglot-platform",
  "version": "2.0.0",
  "active": true
}
''',
            "docs/ARCHITECTURE.md": '''# Architecture Documentation
High-performance polyglot architecture combining Rust, Go, Java, and Solidity.
''',
            "custom/parser.customlang": '''// Custom proprietary language file
DEFINE MODULE custom_flow
BEGIN
  PROCESS INPUT STREAM
END
''',
            ".env": "POLYGLOT_SECRET_KEY=super_confidential_vault_token_xyz999\nDB_SECRET=Pass123!\n",
            "keys/id_rsa": "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAA=\n-----END OPENSSH PRIVATE KEY-----\n",
            "assets/diagram.png": "\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00",
            "node_modules/vue/package.json": '{"name": "vue", "version": "3.0.0"}'
        },
        "pull_requests": {}
    },
    "somularamamaheswarreddy8/ai-phishing-detection-system": {
        "id": 1004,
        "full_name": "somularamamaheswarreddy8/AI-Phishing-Detection-System",
        "owner": "somularamamaheswarreddy8",
        "name": "AI-Phishing-Detection-System",
        "default_branch": "main",
        "is_private": False,
        "is_demo": True,
        "commit_sha": "941571a421d8979c977e62d6c024d504471a02a0",
        "summary": "AI Phishing Detection System with UCI dataset feature extraction, SQLite logging in database.py, and Flask API in app.py.",
        "files": {
            "app.py": '''from flask import Flask, request, jsonify, render_template
from utils import get_uci_features, is_valid_url
from database import init_db, insert_scan, get_recent_scans

app = Flask(__name__)
init_db()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/scan", methods=["POST"])
def scan():
    data = request.get_json() or {}
    target_url = data.get("url", "")
    if not is_valid_url(target_url):
        return jsonify({"error": "Invalid URL"}), 400
    features = get_uci_features(target_url)
    is_phish = features["shortening_service"] == 1 or features["having_at_symbol"] == 1
    result = "Phishing" if is_phish else "Legitimate"
    confidence = 0.94 if is_phish else 0.98
    insert_scan(target_url, result, confidence, "Blocked" if is_phish else "Allowed")
    return jsonify({"url": target_url, "result": result, "confidence": confidence, "features": features})

@app.route("/logs", methods=["GET"])
def get_logs():
    return jsonify({"logs": get_recent_scans(limit=20)})
''',
            "utils.py": '''import re
from urllib.parse import urlparse

def is_valid_url(url: str) -> bool:
    regex = re.compile(
        r'^(?:http|ftp)s?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\\.)+(?:[A-Z]{2,6}\\.?|[A-Z0-9-]{2,}\\.?)|'
        r'localhost|'
        r'\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3})'
        r'(?::\\d+)?'
        r'(?:/?|[/?]\\S+)$', re.IGNORECASE)
    return re.match(regex, url) is not None

def get_uci_features(url: str):
    parsed = urlparse(url)
    features = {
        "having_ip_address": 1 if re.match(r"^\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}$", parsed.netloc) else -1,
        "url_length": 1 if len(url) > 75 else (-1 if len(url) < 54 else 0),
        "shortening_service": 1 if any(s in parsed.netloc for s in ["bit.ly", "goo.gl", "tinyurl"]) else -1,
        "having_at_symbol": 1 if "@" in url else -1,
        "double_slash_redirecting": 1 if url.rfind("//") > 7 else -1,
        "prefix_suffix": 1 if "-" in parsed.netloc else -1,
        "having_sub_domain": 1 if parsed.netloc.count(".") > 2 else -1
    }
    return features
''',
            "database.py": '''import sqlite3
import os
from datetime import datetime

DB_FILE = "threat_logs.db"

def get_connection():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_FILE)
    conn = sqlite3.connect(db_path)
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute(\'\'\'
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            target_vector TEXT,
            analysis_result TEXT,
            confidence REAL,
            action_taken TEXT
        )
    \'\'\')
    conn.commit()
    conn.close()

def insert_scan(target_vector, analysis_result, confidence, action_taken):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now()
    c.execute(\'\'\'
        INSERT INTO scans (timestamp, target_vector, analysis_result, confidence, action_taken)
        VALUES (?, ?, ?, ?, ?)
    \'\'\', (now.isoformat(), target_vector, analysis_result, confidence, action_taken))
    conn.commit()
    conn.close()

def get_recent_scans(limit=10):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM scans ORDER BY id DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    return rows
''',
            "train_email_model.py": '''"""Model training for email phishing detection."""
import re
from typing import List, Dict

def train():
    print("Training email phishing classifier...")
    return {"accuracy": 0.962}
''',
            "train_sms_model.py": '''"""SMS Phishing Dataset Generator and Model Trainer."""
import re

def generate_synthetic_phishing():
    return ["Your bank account is locked. Click here."]

def load_local_csv():
    return []

def train():
    print("Training SMS phishing classifier...")
    return {"accuracy": 0.954}
''',
            "README.md": '''# AI Phishing Detection System
Machine learning and heuristic system detecting phishing URLs, emails, and SMS threats.
Features UCI dataset extraction in `utils.py`, SQLite logging in `database.py`, and Flask web API in `app.py`.
''',
            "requirements.txt": '''flask==3.0.0
scikit-learn==1.3.2
pandas==2.1.4
numpy==1.26.2
'''
        },
        "pull_requests": {}
    }
}


DYNAMIC_REPOSITORIES: Dict[str, Dict[str, Any]] = {}


def get_or_create_synthetic_repo(norm_name: str) -> Dict[str, Any]:
    """Generates a polyglot mock repository tree for offline or rate-limited GitHub demo testing."""
    if norm_name in DYNAMIC_REPOSITORIES:
        return DYNAMIC_REPOSITORIES[norm_name]
    parts = norm_name.split("/")
    owner = parts[0] if len(parts) > 0 else "user"
    name = parts[1] if len(parts) > 1 else norm_name
    commit_sha = hashlib.sha1(norm_name.encode("utf-8")).hexdigest()

    files = {
        "README.md": f"""# {name}

Enterprise project repository for `{norm_name}`.
Analyzed and indexed with RepoSage Evidence-Grounded Engine.

## Modules
- API Gateway & Controllers (`src/server.ts`)
- Authentication & JWT Security (`src/auth.ts`)
- Core Business Logic (`src/service.ts`)
- Test Suite (`tests/service.test.ts`)
""",
        "package.json": f"""{{
  "name": "{name}",
  "version": "1.0.0",
  "description": "Enterprise repository {norm_name}",
  "main": "src/server.ts",
  "dependencies": {{
    "express": "^4.18.2",
    "jsonwebtoken": "^9.0.2",
    "dotenv": "^16.3.1"
  }},
  "devDependencies": {{
    "jest": "^29.7.0",
    "typescript": "^5.2.2"
  }}
}}""",
        "src/server.ts": f"""import express, {{ Request, Response }} from 'express';
import {{ verifyAuthToken }} from './auth';
import {{ executeBusinessLogic }} from './service';

const app = express();
app.use(express.json());

export function startServer(port: number = 3000) {{
  app.get('/health', (req: Request, res: Response) => {{
    res.json({{ status: 'healthy', repository: '{norm_name}' }});
  }});

  app.post('/api/action', (req: Request, res: Response) => {{
    const token = req.headers.authorization?.replace('Bearer ', '');
    const user = verifyAuthToken(token || '');
    if (!user) {{
      return res.status(401).json({{ error: 'Unauthorized' }});
    }}
    const result = executeBusinessLogic(req.body);
    return res.json(result);
  }});

  return app;
}}
""",
        "src/auth.ts": """import crypto from 'crypto';

export interface AuthUser {
  id: string;
  username: string;
}

export function verifyAuthToken(token: string): AuthUser | null {
  if (!token || token.length < 8) {
    return null;
  }
  return { id: 'usr_101', username: 'developer' };
}

export function hashCredential(password: string): string {
  return crypto.createHash('sha256').update(password).digest('hex');
}
""",
        "src/service.ts": """export interface ServiceInput {
  action: string;
  payload?: Record<string, any>;
}

export function executeBusinessLogic(input: ServiceInput): Record<string, any> {
  if (!input || !input.action) {
    throw new Error('Invalid input action');
  }
  return {
    success: true,
    processed_action: input.action,
    timestamp: new Date().toISOString()
  };
}
""",
        "tests/service.test.ts": """import { executeBusinessLogic } from '../src/service';
import { verifyAuthToken } from '../src/auth';

describe('Service Logic Tests', () => {
  it('should execute valid actions', () => {
    const res = executeBusinessLogic({ action: 'process_data' });
    expect(res.success).toBe(true);
    expect(res.processed_action).toBe('process_data');
  });

  it('should reject invalid auth token', () => {
    expect(verifyAuthToken('')).toBeNull();
  });
});
""",
        ".env": "APP_SECRET=demo_insecure_token_xyz999\nDATABASE_URL=postgresql://user:pass@localhost:5432/db\n"
    }

    synthetic_repo = {
        "id": abs(hash(norm_name)) % 100000 + 2000,
        "full_name": norm_name,
        "owner": owner,
        "name": name,
        "default_branch": "main",
        "is_private": False,
        "is_demo": True,
        "commit_sha": commit_sha,
        "summary": f"Enterprise workspace for {norm_name} with TypeScript server, authentication, business services, and Jest unit tests.",
        "files": files,
        "pull_requests": {}
    }
    DYNAMIC_REPOSITORIES[norm_name] = synthetic_repo
    return synthetic_repo


class MockGitHubClient(BaseGitHubClient):
    """
    Mock GitHub Client for offline, demo, and public repository operation.
    Provides complete mock repository trees, and fetches public GitHub repos if available.
    """

    def _get_headers(self) -> Dict[str, str]:
        headers = {"User-Agent": "RepoSage", "Accept": "application/vnd.github.v3+json"}
        token = settings.GITHUB_TOKEN or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def get_repository(self, repo_full_name: str) -> Dict[str, Any]:
        norm_name = normalize_repo_name(repo_full_name)
        repo = MOCK_REPOSITORIES.get(norm_name) or DYNAMIC_REPOSITORIES.get(norm_name)
        if repo:
            return {
                "id": repo["id"],
                "full_name": repo["full_name"],
                "owner": {"login": repo["owner"]},
                "name": repo["name"],
                "default_branch": repo["default_branch"],
                "private": repo["is_private"],
                "is_demo": repo.get("is_demo", True)
            }

        parts = norm_name.split("/")
        owner = parts[0] if len(parts) > 0 else "user"
        name = parts[1] if len(parts) > 1 else norm_name

        # Attempt to query public GitHub API
        try:
            headers = self._get_headers()
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(f"https://api.github.com/repos/{owner}/{name}", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "id": data.get("id", 9999),
                        "full_name": data.get("full_name", norm_name),
                        "owner": {"login": data.get("owner", {}).get("login", owner)},
                        "name": data.get("name", name),
                        "default_branch": data.get("default_branch", "main"),
                        "private": data.get("private", False),
                        "is_demo": False
                    }
                elif resp.status_code == 404:
                    raise ValueError(f"Repository '{norm_name}' not found on GitHub. Please check the spelling.")
                elif resp.status_code == 401 or resp.status_code == 403:
                    logger.warning(
                        f"GitHub API rate limit or auth required for '{norm_name}'. Falling back to synthetic mock repository."
                    )
                    synth = get_or_create_synthetic_repo(norm_name)
                    return {
                        "id": synth["id"],
                        "full_name": synth["full_name"],
                        "owner": {"login": synth["owner"]},
                        "name": synth["name"],
                        "default_branch": synth["default_branch"],
                        "private": synth["is_private"],
                        "is_demo": True
                    }
                else:
                    raise ValueError(f"GitHub returned HTTP {resp.status_code} for '{norm_name}'.")
        except ValueError:
            raise
        except Exception as e:
            logger.warning(f"Could not reach public GitHub for {norm_name}: {e}. Falling back to synthetic mock repository.")
            synth = get_or_create_synthetic_repo(norm_name)
            return {
                "id": synth["id"],
                "full_name": synth["full_name"],
                "owner": {"login": synth["owner"]},
                "name": synth["name"],
                "default_branch": synth["default_branch"],
                "private": synth["is_private"],
                "is_demo": True
            }

    async def get_repository_tree(self, repo_full_name: str, ref: str) -> List[Dict[str, Any]]:
        norm_name = normalize_repo_name(repo_full_name)
        repo = MOCK_REPOSITORIES.get(norm_name) or DYNAMIC_REPOSITORIES.get(norm_name)
        if repo:
            files_map = dict(repo["files"])
            if "branches" in repo:
                branch_info = repo["branches"].get(ref)
                if not branch_info:
                    for b_name, b_val in repo["branches"].items():
                        if b_val.get("commit_sha") == ref:
                            branch_info = b_val
                            break
                if branch_info and "extra_files" in branch_info:
                    files_map.update(branch_info["extra_files"])
            tree = []
            for file_path, content in files_map.items():
                tree.append({
                    "path": file_path,
                    "type": "blob",
                    "size": len(content.encode("utf-8")),
                    "sha": "mocksha_" + file_path.replace("/", "_")
                })
            return tree

        # Attempt public GitHub git tree
        try:
            parts = norm_name.split("/")
            if len(parts) == 2:
                owner, name = parts
                target_ref = ref
                if not target_ref or target_ref.startswith("public_commit_sha"):
                    target_ref = "main"
                headers = self._get_headers()
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.get(
                        f"https://api.github.com/repos/{owner}/{name}/git/trees/{target_ref}?recursive=1",
                        headers=headers
                    )
                    if resp.status_code == 200:
                        tree_items = resp.json().get("tree", [])
                        if tree_items:
                            return tree_items
                    if resp.status_code == 404 and target_ref == "main":
                        resp_master = await client.get(
                            f"https://api.github.com/repos/{owner}/{name}/git/trees/master?recursive=1",
                            headers=headers
                        )
                        if resp_master.status_code == 200:
                            tree_items = resp_master.json().get("tree", [])
                            if tree_items:
                                return tree_items
        except Exception as e:
            logger.warning(f"Failed to fetch git tree from public GitHub for {norm_name}: {e}")

        synth = get_or_create_synthetic_repo(norm_name)
        return [
            {
                "path": file_path,
                "type": "blob",
                "size": len(content.encode("utf-8")),
                "sha": "mocksha_" + file_path.replace("/", "_")
            }
            for file_path, content in synth["files"].items()
        ]

    async def get_file_content(self, repo_full_name: str, file_path: str, ref: str) -> str:
        norm_name = normalize_repo_name(repo_full_name)
        repo = MOCK_REPOSITORIES.get(norm_name) or DYNAMIC_REPOSITORIES.get(norm_name)
        if repo:
            if "branches" in repo:
                branch_info = repo["branches"].get(ref)
                if not branch_info:
                    for b_name, b_val in repo["branches"].items():
                        if b_val.get("commit_sha") == ref:
                            branch_info = b_val
                            break
                if branch_info and "extra_files" in branch_info and file_path in branch_info["extra_files"]:
                    return branch_info["extra_files"][file_path]
            if file_path in repo["files"]:
                return repo["files"][file_path]

        # Fetch from raw.githubusercontent.com
        try:
            parts = norm_name.split("/")
            if len(parts) == 2:
                owner, name = parts
                target_ref = ref
                if not target_ref or target_ref.startswith("public_commit_sha"):
                    target_ref = "main"
                url = f"https://raw.githubusercontent.com/{owner}/{name}/{target_ref}/{file_path}"
                headers = self._get_headers()
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(url, headers=headers)
                    if resp.status_code == 200:
                        return resp.text
                    if resp.status_code == 404 and target_ref == "main":
                        url_master = f"https://raw.githubusercontent.com/{owner}/{name}/master/{file_path}"
                        resp_master = await client.get(url_master, headers=headers)
                        if resp_master.status_code == 200:
                            return resp_master.text
        except Exception as e:
            logger.warning(f"Failed to fetch file content for {file_path} from public GitHub: {e}")

        synth = get_or_create_synthetic_repo(norm_name)
        return synth["files"].get(file_path, "")

    async def get_latest_commit_sha(self, repo_full_name: str, branch: str) -> str:
        norm_name = normalize_repo_name(repo_full_name)
        repo = MOCK_REPOSITORIES.get(norm_name) or DYNAMIC_REPOSITORIES.get(norm_name)
        if repo:
            if "branches" in repo and branch in repo["branches"]:
                return repo["branches"][branch].get("commit_sha", repo["commit_sha"])
            return repo["commit_sha"]

        # Fetch latest commit SHA from public GitHub
        try:
            parts = norm_name.split("/")
            if len(parts) == 2:
                owner, name = parts
                headers = self._get_headers()
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        f"https://api.github.com/repos/{owner}/{name}/commits/{branch}",
                        headers=headers
                    )
                    if resp.status_code == 200:
                        return resp.json()["sha"]
                    if resp.status_code == 404 and branch == "main":
                        resp_master = await client.get(
                            f"https://api.github.com/repos/{owner}/{name}/commits/master",
                            headers=headers
                        )
                        if resp_master.status_code == 200:
                            return resp_master.json()["sha"]
        except Exception as e:
            logger.warning(f"Could not get commit sha from public GitHub for {norm_name}: {e}")

        synth = get_or_create_synthetic_repo(norm_name)
        return synth.get("commit_sha", f"commit_{norm_name.replace('/', '_')}")

    async def get_pull_request(self, repo_full_name: str, pr_number: int) -> Dict[str, Any]:
        norm_name = normalize_repo_name(repo_full_name)
        repo = MOCK_REPOSITORIES.get(norm_name)
        if repo and pr_number in repo["pull_requests"]:
            pr = repo["pull_requests"][pr_number]
            return {
                "number": pr["number"],
                "title": pr["title"],
                "base": {"sha": pr["base_sha"]},
                "head": {"sha": pr["head_sha"]},
                "state": "open"
            }

        # Attempt to fetch public PR from GitHub
        try:
            parts = norm_name.split("/")
            if len(parts) == 2:
                owner, name = parts
                headers = self._get_headers()
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        f"https://api.github.com/repos/{owner}/{name}/pulls/{pr_number}",
                        headers=headers
                    )
                    if resp.status_code == 200:
                        return resp.json()
        except Exception:
            pass

        return {
            "number": pr_number,
            "title": f"PR #{pr_number}: Updates",
            "base": {"sha": "base_sha_000"},
            "head": {"sha": "head_sha_111"},
            "state": "open"
        }

    async def get_pull_request_diff(self, repo_full_name: str, pr_number: int) -> str:
        norm_name = normalize_repo_name(repo_full_name)
        repo = MOCK_REPOSITORIES.get(norm_name)
        if repo and pr_number in repo["pull_requests"]:
            return repo["pull_requests"][pr_number]["diff"]

        # Attempt to fetch public PR diff from GitHub
        try:
            parts = norm_name.split("/")
            if len(parts) == 2:
                owner, name = parts
                headers = {"User-Agent": "RepoSage", "Accept": "application/vnd.github.v3.diff"}
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        f"https://api.github.com/repos/{owner}/{name}/pulls/{pr_number}",
                        headers=headers
                    )
                    if resp.status_code == 200:
                        return resp.text
        except Exception:
            pass

        return """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,3 +1,4 @@
 def main():
+    # Updates in PR
     return True
"""

    async def publish_review_comments(
        self,
        repo_full_name: str,
        pr_number: int,
        commit_sha: str,
        comments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        published = []
        for i, c in enumerate(comments):
            pub = {
                "id": f"gh_comment_{i + 1}_{int(datetime.datetime.utcnow().timestamp())}",
                "path": c.get("path"),
                "line": c.get("line"),
                "body": c.get("body"),
                "created_at": datetime.datetime.utcnow().isoformat() + "Z"
            }
            published.append(pub)
            logger.info(f"[GITHUB SERVICE] Published approved comment to {repo_full_name}#PR{pr_number} at {c.get('path')}:{c.get('line')}")
        return published

    async def publish_advisory_check(
        self,
        repo_full_name: str,
        head_sha: str,
        title: str,
        summary: str,
        conclusion: str = "neutral"
    ) -> Dict[str, Any]:
        logger.info(f"[GITHUB SERVICE] Published advisory check for {repo_full_name}@{head_sha[:7]}: {title} [{conclusion}]")
        return {
            "id": "check_run_12345",
            "name": "RepoSage / Advisory Review",
            "head_sha": head_sha,
            "status": "completed",
            "conclusion": conclusion,
            "title": title,
            "summary": summary
        }
