# Тестовое задание

## Инструкция по запуску

```sh
# Сборка контейнеров
docker compose up -d --build

# Запуск интеграционного тестирование (тестирование API)
pytest tests/integration/ -v -s

# Запуск нагрузочного тестирования
python tests/load/run_load_test.py 
```