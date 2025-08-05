import time
import threading
from collections import defaultdict, deque
from typing import Dict, List, Optional
import math

class FixedWindowRateLimiter:
    """
    Fixed Window Counter Algorithm
    - Simple and memory efficient
    - Has burst problem at window boundaries
    """
    
    def __init__(self, limit: int, window_size: int):
        self.limit = limit
        self.window_size = window_size  # in seconds
        self.counters: Dict[str, Dict] = defaultdict(lambda: {'count': 0, 'window_start': 0})
        self.lock = threading.Lock()
    
    def is_allowed(self, key: str) -> bool:
        with self.lock:
            current_time = time.time()
            current_window = int(current_time // self.window_size)
            
            counter_data = self.counters[key]
            
            # Reset counter if we're in a new window
            if counter_data['window_start'] != current_window:
                counter_data['count'] = 0
                counter_data['window_start'] = current_window
            
            # Check if request is allowed
            if counter_data['count'] < self.limit:
                counter_data['count'] += 1
                return True
            
            return False
    
    def get_stats(self, key: str) -> Dict:
        counter_data = self.counters[key]
        return {
            'requests_made': counter_data['count'],
            'limit': self.limit,
            'remaining': max(0, self.limit - counter_data['count']),
            'window_start': counter_data['window_start']
        }


class SlidingWindowLogRateLimiter:
    """
    Sliding Window Log Algorithm
    - Most accurate but memory intensive
    - Stores timestamp of every request
    """
    
    def __init__(self, limit: int, window_size: int):
        self.limit = limit
        self.window_size = window_size
        self.logs: Dict[str, deque] = defaultdict(deque)
        self.lock = threading.Lock()
    
    def is_allowed(self, key: str) -> bool:
        with self.lock:
            current_time = time.time()
            request_log = self.logs[key]
            
            # Remove expired requests
            cutoff_time = current_time - self.window_size
            while request_log and request_log[0] < cutoff_time:
                request_log.popleft()
            
            # Check if request is allowed
            if len(request_log) < self.limit:
                request_log.append(current_time)
                return True
            
            return False
    
    def get_stats(self, key: str) -> Dict:
        current_time = time.time()
        request_log = self.logs[key]
        
        # Count requests in current window
        cutoff_time = current_time - self.window_size
        active_requests = sum(1 for timestamp in request_log if timestamp >= cutoff_time)
        
        return {
            'requests_made': active_requests,
            'limit': self.limit,
            'remaining': max(0, self.limit - active_requests),
            'oldest_request': request_log[0] if request_log else None
        }


class SlidingWindowCounterRateLimiter:
    """
    Sliding Window Counter Algorithm
    - Balance between accuracy and efficiency
    - Uses weighted count from previous window
    """
    
    def __init__(self, limit: int, window_size: int):
        self.limit = limit
        self.window_size = window_size
        self.windows: Dict[str, Dict] = defaultdict(lambda: {'current': 0, 'previous': 0, 'current_start': 0})
        self.lock = threading.Lock()
    
    def is_allowed(self, key: str) -> bool:
        with self.lock:
            current_time = time.time()
            current_window = int(current_time // self.window_size)
            
            window_data = self.windows[key]
            
            # Check if we need to slide the window
            if window_data['current_start'] != current_window:
                if window_data['current_start'] == current_window - 1:
                    # Move to next window
                    window_data['previous'] = window_data['current']
                else:
                    # Jumped multiple windows (user was inactive)
                    window_data['previous'] = 0
                
                window_data['current'] = 0
                window_data['current_start'] = current_window
            
            # Calculate weighted count
            time_in_current_window = current_time - (current_window * self.window_size)
            weight = 1 - (time_in_current_window / self.window_size)
            weighted_count = (window_data['previous'] * weight) + window_data['current']
            
            # Check if request is allowed
            if weighted_count < self.limit:
                window_data['current'] += 1
                return True
            
            return False
    
    def get_stats(self, key: str) -> Dict:
        current_time = time.time()
        current_window = int(current_time // self.window_size)
        window_data = self.windows[key]
        
        time_in_current_window = current_time - (current_window * self.window_size)
        weight = 1 - (time_in_current_window / self.window_size)
        weighted_count = (window_data['previous'] * weight) + window_data['current']
        
        return {
            'weighted_count': weighted_count,
            'current_window_requests': window_data['current'],
            'previous_window_requests': window_data['previous'],
            'limit': self.limit,
            'remaining': max(0, self.limit - weighted_count)
        }


class TokenBucketRateLimiter:
    """
    Token Bucket Algorithm
    - Excellent for handling bursts
    - Tokens are added at a steady rate
    """
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity  # max tokens in bucket
        self.refill_rate = refill_rate  # tokens per second
        self.buckets: Dict[str, Dict] = defaultdict(lambda: {
            'tokens': capacity,
            'last_refill': time.time()
        })
        self.lock = threading.Lock()
    
    def is_allowed(self, key: str, tokens_requested: int = 1) -> bool:
        with self.lock:
            current_time = time.time()
            bucket = self.buckets[key]
            
            # Refill tokens
            time_passed = current_time - bucket['last_refill']
            tokens_to_add = time_passed * self.refill_rate
            bucket['tokens'] = min(self.capacity, bucket['tokens'] + tokens_to_add)
            bucket['last_refill'] = current_time
            
            # Check if request is allowed
            if bucket['tokens'] >= tokens_requested:
                bucket['tokens'] -= tokens_requested
                return True
            
            return False
    
    def get_stats(self, key: str) -> Dict:
        bucket = self.buckets[key]
        return {
            'available_tokens': bucket['tokens'],
            'capacity': self.capacity,
            'refill_rate': self.refill_rate,
            'last_refill': bucket['last_refill']
        }


class LeakyBucketRateLimiter:
    """
    Leaky Bucket Algorithm
    - Smooths traffic by processing requests at fixed rate
    - Can introduce latency as requests are queued
    """
    
    def __init__(self, capacity: int, leak_rate: float):
        self.capacity = capacity  # max queue size
        self.leak_rate = leak_rate  # requests processed per second
        self.buckets: Dict[str, Dict] = defaultdict(lambda: {
            'queue': deque(),
            'last_leak': time.time()
        })
        self.lock = threading.Lock()
    
    def is_allowed(self, key: str) -> bool:
        with self.lock:
            current_time = time.time()
            bucket = self.buckets[key]
            
            # Leak (process) requests from queue
            time_passed = current_time - bucket['last_leak']
            requests_to_leak = int(time_passed * self.leak_rate)
            
            for _ in range(min(requests_to_leak, len(bucket['queue']))):
                bucket['queue'].popleft()
            
            bucket['last_leak'] = current_time
            
            # Check if we can add new request to queue
            if len(bucket['queue']) < self.capacity:
                bucket['queue'].append(current_time)
                return True
            
            return False
    
    def get_stats(self, key: str) -> Dict:
        bucket = self.buckets[key]
        return {
            'queue_size': len(bucket['queue']),
            'capacity': self.capacity,
            'leak_rate': self.leak_rate,
            'last_leak': bucket['last_leak']
        }


# Demonstration and Testing
def test_rate_limiters():
    """Test all rate limiting algorithms with practical examples"""
    
    print("=== Rate Limiting Algorithms Demo ===\n")
    
    # Test 1: Fixed Window - Show burst problem
    print("1. Fixed Window Rate Limiter (Burst Problem Demo)")
    print("Limit: 5 requests per 10 seconds")
    fixed_limiter = FixedWindowRateLimiter(limit=5, window_size=10)
    
    # Make 5 requests quickly
    for i in range(7):
        allowed = fixed_limiter.is_allowed("user1")
        stats = fixed_limiter.get_stats("user1")
        print(f"Request {i+1}: {'✓ Allowed' if allowed else '✗ Denied'} "
              f"({stats['requests_made']}/{stats['limit']})")
        if i == 4:  # After 5th request, wait for next window
            print("Waiting for new window...")
            time.sleep(11)
    
    print()
    
    # Test 2: Token Bucket - Show burst handling
    print("2. Token Bucket Rate Limiter (Burst Handling Demo)")
    print("Capacity: 5 tokens, Refill: 1 token/second")
    token_limiter = TokenBucketRateLimiter(capacity=5, refill_rate=1.0)
    
    # Burst of 5 requests
    print("Making 5 requests quickly (burst):")
    for i in range(5):
        allowed = token_limiter.is_allowed("user2")
        stats = token_limiter.get_stats("user2")
        print(f"Request {i+1}: {'✓ Allowed' if allowed else '✗ Denied'} "
              f"(Tokens: {stats['available_tokens']:.1f})")
    
    # 6th request should be denied
    allowed = token_limiter.is_allowed("user2")
    stats = token_limiter.get_stats("user2")
    print(f"Request 6: {'✓ Allowed' if allowed else '✗ Denied'} "
          f"(Tokens: {stats['available_tokens']:.1f})")
    
    # Wait and try again
    print("Waiting 3 seconds for token refill...")
    time.sleep(3)
    allowed = token_limiter.is_allowed("user2")
    stats = token_limiter.get_stats("user2")
    print(f"After wait: {'✓ Allowed' if allowed else '✗ Denied'} "
          f"(Tokens: {stats['available_tokens']:.1f})")
    
    print()
    
    # Test 3: Sliding Window Log - Show accuracy
    print("3. Sliding Window Log Rate Limiter (Accuracy Demo)")
    print("Limit: 3 requests per 5 seconds")
    sliding_limiter = SlidingWindowLogRateLimiter(limit=3, window_size=5)
    
    for i in range(5):
        allowed = sliding_limiter.is_allowed("user3")
        stats = sliding_limiter.get_stats("user3")
        print(f"Request {i+1}: {'✓ Allowed' if allowed else '✗ Denied'} "
              f"({stats['requests_made']}/{stats['limit']})")
        if i == 2:  # After 3rd request
            print("Waiting 6 seconds for window to slide...")
            time.sleep(6)
    
    print()
    
    # Test 4: Compare all algorithms
    print("4. Algorithm Comparison (10 requests/minute)")
    print("Time | Fixed | Sliding | Token | Leaky")
    print("-" * 40)
    
    # Initialize all limiters with same logical limit
    fixed = FixedWindowRateLimiter(limit=10, window_size=60)
    sliding = SlidingWindowLogRateLimiter(limit=10, window_size=60)
    token = TokenBucketRateLimiter(capacity=10, refill_rate=10/60)  # 10 tokens per minute
    leaky = LeakyBucketRateLimiter(capacity=10, leak_rate=10/60)  # 10 requests per minute
    
    # Test with burst pattern
    test_times = [0, 0, 0, 0, 0, 30, 30, 35, 60, 65]  # Requests at different times
    
    start_time = time.time()
    for i, delay in enumerate(test_times):
        # Simulate time passing
        target_time = start_time + delay
        current_time = time.time()
        if target_time > current_time:
            time.sleep(target_time - current_time)
        
        elapsed = int(time.time() - start_time)
        fixed_ok = fixed.is_allowed("test")
        sliding_ok = sliding.is_allowed("test")
        token_ok = token.is_allowed("test")
        leaky_ok = leaky.is_allowed("test")
        
        print(f"{elapsed:4d}s | {'✓' if fixed_ok else '✗':5} | {'✓' if sliding_ok else '✗':7} | "
              f"{'✓' if token_ok else '✗':5} | {'✓' if leaky_ok else '✗':5}")


# Usage examples for different scenarios
def usage_examples():
    """Show practical usage patterns for different scenarios"""
    
    print("\n=== Practical Usage Examples ===\n")
    
    # API Rate Limiting
    print("API Rate Limiting Example:")
    api_limiter = TokenBucketRateLimiter(capacity=100, refill_rate=10)  # 100 burst, 10/sec sustained
    
    def api_endpoint(user_id: str, endpoint: str):
        key = f"{user_id}:{endpoint}"
        if api_limiter.is_allowed(key):
            return {"status": "success", "data": "API response"}
        else:
            stats = api_limiter.get_stats(key)
            return {
                "status": "rate_limited", 
                "message": f"Rate limit exceeded. Available tokens: {stats['available_tokens']:.1f}"
            }
    
    # Simulate API calls
    for i in range(5):
        result = api_endpoint("user123", "/posts")
        print(f"API Call {i+1}: {result['status']}")
    
    print()
    
    # Login Attempt Rate Limiting
    print("Login Attempt Rate Limiting:")
    login_limiter = FixedWindowRateLimiter(limit=5, window_size=300)  # 5 attempts per 5 minutes
    
    def login_attempt(username: str):
        if login_limiter.is_allowed(f"login:{username}"):
            return "Login attempt allowed"
        else:
            return "Too many login attempts. Please wait 5 minutes."
    
    # Simulate failed login attempts
    for i in range(7):
        result = login_attempt("user456")
        print(f"Login attempt {i+1}: {result}")


if __name__ == "__main__":
    test_rate_limiters()
    usage_examples()