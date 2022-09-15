Запуск сервиса:

docker-compose up --build -d

Генерация и применение миграций:

docker exec -it app bash

cd app && alembic revision --autogenerate -m "First Migration" && alembic upgrade head


В решении подразумевается, что файлов в /imports загружается столько, сколько элементов типа "FILE" в JSON.
