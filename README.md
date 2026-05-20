# Тестовое задание

[📊 Просмотр отчета](https://htmlpreview.github.io/?https://github.com/username/repo/blob/main/tests/load/Load%20Test%20Bottleneck%20Report.html)

## Инструкция по запуску

```sh
# Сборка контейнеров
docker compose up -d --build

# Запуск интеграционного тестирование (тестирование API)
pytest tests/integration/ -v -s

# Запуск нагрузочного тестирования
python tests/load/run_load_test.py 
```
