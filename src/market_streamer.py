"""
Market Data Streamer - Simulates real-time market data feed
Publishes to Redis for consumption by Pathway pipeline
"""

import os
import time
import json
import redis
import logging
from datetime import datetime
from typing import Dict, List
import random
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MarketDataStreamer:
    """Streams live market data to Redis"""
    
    def __init__(
        self,
        redis_host: str = "redis",
        redis_port: int = 6379,
        stream_interval: int = 10,
        watchlist: List[str] = None,
    ):
        self.redis_client = None
        self.connect_redis_with_retries(redis_host, redis_port)
        self.stream_interval = stream_interval
        self.watchlist = watchlist or [
            "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
            "NVDA", "META", "JPM", "BAC", "WFC"
        ]
        
        # API keys
        self.alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        self.finnhub_key = os.getenv("FINNHUB_API_KEY")
        
        # Price cache for simulation
        self.price_cache = {}
        
        logger.info(f"Market Streamer initialized with {len(self.watchlist)} symbols")
    
    def fetch_real_data(self, symbol: str) -> Dict:
        """Fetch real market data from APIs (rate limited)"""
        try:
            if not self.finnhub_key:
                logger.debug(f"Finnhub API key not configured")
                return None
                
            url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={self.finnhub_key}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "symbol": symbol,
                    "price": data.get("c", 0),  # current price
                    "change_pct": data.get("dp", 0),  # percent change
                    "volume": data.get("v", 0),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            elif response.status_code == 401:
                logger.error(f"Finnhub API key invalid")
            else:
                logger.debug(f"Finnhub API returned status {response.status_code}")
        except Exception as e:
            logger.warning(f"Error fetching real data for {symbol}: {e}")
        
        return None
    
    def simulate_market_data(self, symbol: str) -> Dict:
        """Simulate realistic market data with random walk"""
        
        # Initialize or get cached price
        if symbol not in self.price_cache:
            # Set realistic starting prices
            base_prices = {
                "AAPL": 180.0, "MSFT": 380.0, "GOOGL": 140.0,
                "AMZN": 145.0, "TSLA": 250.0, "NVDA": 480.0,
                "META": 350.0, "JPM": 160.0, "BAC": 35.0, "WFC": 45.0
            }
            self.price_cache[symbol] = base_prices.get(symbol, 100.0)
        
        current_price = self.price_cache[symbol]
        
        # Random walk with slight upward bias
        change_pct = random.gauss(0.1, 1.5)  # mean=0.1%, std=1.5%
        new_price = current_price * (1 + change_pct / 100)
        
        # Add occasional volatility spikes (15% chance)
        if random.random() < 0.15:
            spike = random.choice([-1, 1]) * random.uniform(5, 20)
            change_pct += spike
            new_price = current_price * (1 + change_pct / 100)
        
        # Update cache
        self.price_cache[symbol] = new_price
        
        # Simulate volume
        base_volume = 1000000
        volume = int(base_volume * random.uniform(0.5, 2.0))
        
        # Sector mapping
        sectors = {
            "AAPL": "Technology", "MSFT": "Technology", "GOOGL": "Technology",
            "AMZN": "Consumer Cyclical", "TSLA": "Automotive",
            "NVDA": "Technology", "META": "Technology",
            "JPM": "Financial", "BAC": "Financial", "WFC": "Financial"
        }
        
        return {
            "symbol": symbol,
            "price": round(new_price, 2),
            "change_pct": round(change_pct, 2),
            "volume": volume,
            "market_cap": round(new_price * volume * 100, 0),
            "sector": sectors.get(symbol, "Other"),
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def publish_market_data(self, data: Dict):
        """Publish market data to Redis stream"""
        try:
            if not self.redis_client:
                logger.warning("Redis client not available; skipping publish")
                return

            self.redis_client.publish("market_data", json.dumps(data))
            logger.debug(f"Published: {data['symbol']} @ ${data['price']} ({data['change_pct']:+.2f}%)")
        except Exception as e:
            logger.error(f"Error publishing data: {e}")

    def connect_redis_with_retries(self, host: str, port: int, retries: int = 12, delay: int = 5):
        """Attempt to connect to Redis with retries and backoff.

        This helps when services start at different times or when running the streamer
        from the host where the service name `redis` may not resolve.
        """
        import socket

        attempt = 0
        while attempt < retries:
            attempt += 1
            try:
                # Try DNS resolution first to give a clear error if host is unknown
                socket.gethostbyname(host)
                client = redis.Redis(host=host, port=port, decode_responses=True)
                client.ping()
                self.redis_client = client
                logger.info(f"Connected to Redis at {host}:{port}")
                return
            except Exception as e:
                logger.warning(f"Redis connection attempt {attempt}/{retries} failed: {e}")
                time.sleep(delay)

        logger.error(f"Could not connect to Redis at {host}:{port} after {retries} attempts")
    
    def stream_market_data(self):
        """Continuously stream market data"""
        logger.info("Starting market data stream...")
        
        iteration = 0
        while True:
            try:
                iteration += 1
                logger.info(f"Streaming cycle {iteration}")
                
                for symbol in self.watchlist:
                    # Try real data first, fallback to simulation
                    data = self.fetch_real_data(symbol)
                    
                    if not data:
                        data = self.simulate_market_data(symbol)
                    
                    self.publish_market_data(data)
                    
                    # Small delay between symbols
                    time.sleep(0.5)
                
                # Log significant changes
                for symbol, price in self.price_cache.items():
                    if symbol in self.watchlist:
                        logger.info(f"{symbol}: ${price:.2f}")
                
                # Wait before next cycle
                logger.info(f"Waiting {self.stream_interval} seconds...")
                time.sleep(self.stream_interval)
                
            except KeyboardInterrupt:
                logger.info("Market streamer stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in streaming loop: {e}")
                time.sleep(5)


def main():
    """Main entry point"""
    
    streamer = MarketDataStreamer(
        redis_host=os.getenv("REDIS_HOST", "redis"),
        redis_port=int(os.getenv("REDIS_PORT", 6379)),
        stream_interval=int(os.getenv("STREAM_INTERVAL", 10)),
    )
    
    streamer.stream_market_data()


if __name__ == "__main__":
    main()