import pytest


@pytest.mark.asyncio
async def test_scenario_3_branching_mathematics(client):
    """
    Сценарий 3: Ветвящийся — Ветка А (математика)
    1. Пользователь: «Хочу выучить что-нибудь новое. Предложи тему: математика или история»
    2. Модель предлагает темы
    3. Пользователь: «математика»
    4. Проверка: ответ модели связан с математикой
    """
    
    first_request = {
        "message": "Хочу выучить что-нибудь новое. Предложи тему: математика или история."
    }
    
    response1 = await client.post("/chat", json=first_request)
    assert response1.status_code == 200
    data1 = response1.json()
    
    session_id = data1["session_id"]
    first_assistant_response = data1["assistant_message"]["content"].lower()
    
    assert "математик" in first_assistant_response or "истори" in first_assistant_response
    
    second_request = {
        "message": "Давай математику",
        "session_id": session_id
    }
    
    response2 = await client.post("/chat", json=second_request)
    assert response2.status_code == 200
    data2 = response2.json()
    
    assert data2["session_id"] == session_id
    second_assistant_response = data2["assistant_message"]["content"].lower()
    
    math_keywords = ["математик", "числ", "арифметик", "алгебр", "геометри", "формул"]
    contains_math = any(keyword in second_assistant_response for keyword in math_keywords)
    assert contains_math, f"Response doesn't contain math keywords: {second_assistant_response[:200]}"
    
    history_response = await client.get(f"/chat/{session_id}")
    assert history_response.status_code == 200
    history_data = history_response.json()
    
    assert len(history_data["messages"]) == 4


@pytest.mark.asyncio
async def test_scenario_3_branching_history(client):
    """
    Сценарий 3: Ветвящийся — Ветка Б (история)
    1. Пользователь: «Хочу выучить что-нибудь новое. Предложи тему: математика или история»
    2. Модель предлагает темы
    3. Пользователь: «история»
    4. Проверка: ответ модели связан с историей
    """
    
    first_request = {
        "message": "Хочу выучить что-нибудь новое. Предложи тему: математика или история."
    }
    
    response1 = await client.post("/chat", json=first_request)
    assert response1.status_code == 200
    data1 = response1.json()
    
    session_id = data1["session_id"]
    
    second_request = {
        "message": "Давай историю",
        "session_id": session_id
    }
    
    response2 = await client.post("/chat", json=second_request)
    assert response2.status_code == 200
    data2 = response2.json()
    
    assert data2["session_id"] == session_id
    second_assistant_response = data2["assistant_message"]["content"].lower()
    
    history_keywords = ["истори", "событи", "прошл", "цивилизац", "древн", "войн", "эпох"]
    contains_history = any(keyword in second_assistant_response for keyword in history_keywords)
    assert contains_history, f"Response doesn't contain history keywords: {second_assistant_response[:200]}"
    
    history_response = await client.get(f"/chat/{session_id}")
    assert history_response.status_code == 200
    history_data = history_response.json()
    
    assert len(history_data["messages"]) == 4


@pytest.mark.asyncio
async def test_scenario_3_branching_different_sessions(client):
    """
    Сценарий 3: Ветвящийся — две разные сессии с разным выбором
    Показывает, что один и тот же начальный запрос ведет к разным веткам диалога
    """
    
    request_a1 = {
        "message": "Предложи тему для изучения: математика или история?"
    }
    
    response_a1 = await client.post("/chat", json=request_a1)
    assert response_a1.status_code == 200
    session_a = response_a1.json()["session_id"]
    
    request_a2 = {
        "message": "Выбираю математику",
        "session_id": session_a
    }
    
    response_a2 = await client.post("/chat", json=request_a2)
    assert response_a2.status_code == 200
    
    request_b1 = {
        "message": "Предложи тему для изучения: математика или история?"
    }
    
    response_b1 = await client.post("/chat", json=request_b1)
    assert response_b1.status_code == 200
    session_b = response_b1.json()["session_id"]
    
    request_b2 = {
        "message": "Выбираю историю",
        "session_id": session_b
    }
    
    response_b2 = await client.post("/chat", json=request_b2)
    assert response_b2.status_code == 200
    
    assert session_a != session_b
    
    response_a_content = response_a2.json()["assistant_message"]["content"].lower()
    response_b_content = response_b2.json()["assistant_message"]["content"].lower()
    
    assert response_a_content != response_b_content
    
    history_a = await client.get(f"/chat/{session_a}")
    history_b = await client.get(f"/chat/{session_b}")
    
    assert history_a.status_code == 200
    assert history_b.status_code == 200
    
    assert len(history_a.json()["messages"]) == 4
    assert len(history_b.json()["messages"]) == 4