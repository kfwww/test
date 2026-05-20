import pytest


@pytest.mark.asyncio
async def test_scenario_2_multiple_messages(client):
    """
    Сценарий 2: Линейный — несколько сообщений подряд
    1. Пользователь: «Привет!»
    2. Модель отвечает
    3. Пользователь: «Как тебя зовут?»
    4. Ожидание: ответ модели содержит имя или описание ассистента
    5. Проверка: в истории 4 сообщения (2 от user, 2 от assistant)
    """
    
    first_request = {
        "message": "Привет!"
    }
    
    response1 = await client.post("/chat", json=first_request)
    assert response1.status_code == 200
    data1 = response1.json()
    
    session_id = data1["session_id"]
    
    assert data1["user_message"]["content"] == "Привет!"
    assert data1["user_message"]["role"] == "user"
    assert data1["assistant_message"]["role"] == "assistant"

    assert len(data1["assistant_message"]["content"]) > 0
    
    second_request = {
        "message": "Как тебя зовут?",
        "session_id": session_id
    }
    
    response2 = await client.post("/chat", json=second_request)
    assert response2.status_code == 200
    data2 = response2.json()
    
    assert data2["session_id"] == session_id
    assert data2["user_message"]["content"] == "Как тебя зовут?"
    assert data2["user_message"]["role"] == "user"
    assert data2["assistant_message"]["role"] == "assistant"
    
    assistant_response = data2["assistant_message"]["content"].lower()
    name_keywords = ["зовут", "имя", "ассистент", "assistant", "помощник", "я", "меня"]
    contains_name = any(keyword in assistant_response for keyword in name_keywords)
    assert contains_name, f"Response doesn't contain assistant name/description: {assistant_response[:200]}"
    
    history_response = await client.get(f"/chat/{session_id}")
    assert history_response.status_code == 200
    history_data = history_response.json()
    
    messages = history_data["messages"]
    assert len(messages) == 4, f"Expected 4 messages, got {len(messages)}"
    
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Привет!"
    
    assert messages[1]["role"] == "assistant"
    
    assert messages[2]["role"] == "user"
    assert messages[2]["content"] == "Как тебя зовут?"
    
    assert messages[3]["role"] == "assistant"
    
    for msg in messages:
        assert msg["session_id"] == session_id