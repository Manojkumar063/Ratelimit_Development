<img width="1897" height="938" alt="Screenshot 2025-08-05 143410" src="https://github.com/user-attachments/assets/d2ac3e76-5df8-4bd9-aee9-952546086f98" />
<img width="686" height="342" alt="image" src="https://github.com/user-attachments/assets/57f97fa8-5390-442d-8b93-37d3493cdcd8" />

# RateLimiter Development 🚦

A Python-based implementation of various **rate limiting algorithms**, designed for developers and engineers to learn, compare, and integrate different throttling strategies in APIs, authentication systems, or other request-intensive environments.

---

## 🚀 Features

- ✅ Fixed Window Counter
- ✅ Sliding Window Log
- ✅ Sliding Window Counter
- ✅ Token Bucket
- ✅ Leaky Bucket
- 🧪 Demonstration scripts with simulated scenarios
- 📊 Usage examples for real-world applications

---

## 📌 Algorithms Included

### 1. **Fixed Window Counter**
- Tracks request count per fixed time window.
- Efficient but can allow bursts at window edges.

### 2. **Sliding Window Log**
- Stores exact timestamps of each request.
- Most accurate but memory intensive.

### 3. **Sliding Window Counter**
- Uses a weighted count from the previous and current window.
- A balance between accuracy and efficiency.

### 4. **Token Bucket**
- Allows bursts and smooths requests over time.
- Refill rate defines steady state throughput.

### 5. **Leaky Bucket**
- Smooths traffic at a constant leak rate.
- Introduces latency via queuing.

---

## 🛠️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/Manojkumar063/Ratelimit_Development.git
cd Ratelimit_Development
