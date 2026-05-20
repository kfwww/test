from locust import HttpUser, task, between, events
import uuid
import random



class ChatUser(HttpUser):
    """Пользователь, имитирующий диалоги по сценариям"""
    
    wait_time = between(1, 3)
    
    def on_start(self):
        self.session_id = None
        self.user_id = str(uuid.uuid4())
    
    @task(3)
    def scenario_1_simple_question(self):
        with self.client.post("/chat", 
            json={"message": "Сколько будет 2 + 2?"},
            catch_response=True,
            name="/chat [Scenario 1]"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "4" not in data.get("assistant_message", {}).get("content", ""):
                    response.failure("Response missing '4'")
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(2)
    def scenario_2_multi_messages(self):
        session_id = str(uuid.uuid4())
        
        with self.client.post("/chat",
            json={"message": "Привет!", "session_id": session_id},
            catch_response=True,
            name="/chat [Scenario 2 - Hello]"
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Failed: {resp.status_code}")
                return
        
        with self.client.post("/chat",
            json={"message": "Как тебя зовут?", "session_id": session_id},
            catch_response=True,
            name="/chat [Scenario 2 - Name]"
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Failed: {resp.status_code}")
        
        with self.client.get(f"/chat/{session_id}",
            catch_response=True,
            name="/chat [Scenario 2 - History]"
        ) as resp:
            if resp.status_code == 200:
                if len(resp.json().get("messages", [])) != 4:
                    resp.failure("Wrong message count")
            else:
                resp.failure(f"Failed: {resp.status_code}")
    
    @task(1)
    def scenario_3_branching(self):
        session_id = str(uuid.uuid4())
        
        with self.client.post("/chat",
            json={"message": "Хочу выучить что-то новое. Предложи тему: математика или история.", "session_id": session_id},
            catch_response=True,
            name="/chat [Scenario 3 - Topic]"
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Failed: {resp.status_code}")
                return
        
        branch = random.choice(["математика", "история"])
        keywords = ["математик", "числ", "арифметик"] if branch == "математика" else ["истори", "событи", "прошл"]
        
        with self.client.post("/chat",
            json={"message": f"Давай {branch}", "session_id": session_id},
            catch_response=True,
            name=f"/chat [Scenario 3 - {branch}]"
        ) as resp:
            if resp.status_code == 200:
                content = resp.json().get("assistant_message", {}).get("content", "").lower()
                if not any(kw in content for kw in keywords):
                    resp.failure(f"No {branch} keywords")
            else:
                resp.failure(f"Failed: {resp.status_code}")


@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    """Вывод итоговой статистики"""
    stats = environment.stats.total
    if stats.num_requests > 0:
        print("\n" + "=" * 60)
        print("LOAD TEST SUMMARY")
        print("=" * 60)
        print(f"Requests:    {stats.num_requests}")
        print(f"Failures:    {stats.num_failures}")
        print(f"Error rate:  {stats.fail_ratio * 100:.2f}%")
        print(f"Avg (ms):    {stats.avg_response_time:.0f}")
        print(f"Median (ms): {stats.median_response_time:.0f}")
        print(f"P95 (ms):    {stats.get_response_time_percentile(0.95):.0f}")
        print(f"P99 (ms):    {stats.get_response_time_percentile(0.99):.0f}")
        print(f"Max (ms):    {stats.max_response_time:.0f}")
        print(f"RPS:         {stats.current_rps:.2f}")
        print("=" * 60)