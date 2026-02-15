#!/usr/bin/env python3
from app.main import app

print("App routes count:", len(app.routes))
print("Routes:")
for route in app.routes:
    if hasattr(route, "path"):
        print(f"  {route.path} - {route.methods}")
    
print("\nMarket data routes:")
for route in app.routes:
    if hasattr(route, "path") and "market-data" in route.path:
        print(f"  {route.path} - {route.methods}")