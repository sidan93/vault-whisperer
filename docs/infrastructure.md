# Infrastructure

## VPS Configuration

| Параметр | Значение |
|---|---|
| Провайдер | (RU VPS) |
| Зона | Москва PA2 |
| ОС | Ubuntu 24.04 |
| CPU | 1 vCPU — Intel Ice Lake (Xeon Gen3) |
| RAM | 2 GB |
| Диск | 30 GB High-IOPS SSD (10 000 IOPS read / 5 000 IOPS write) |
| Внешний IP | да |
| DNS-имя | local-vault |
| Подсеть | 10.0.0.0/24 |
| Имя ВМ | local_vault |

## Firewall

| Порт | Протокол | Зачем |
|---|---|---|
| 22 | TCP | SSH — управление сервером |
| 443 | TCP | Telegram webhook (если используется) |

> Порт 80 не открыт — веб-интерфейса нет, nginx/certbot не используется.

## Резервное копирование

Отдельный бекап не нужен:

- **Заметки (vault)** → автоматически пушатся в GitHub через `git-sync` после каждой записи
- **Код** → GitHub
- **ChromaDB индекс** → производные данные, пересобираются из vault при необходимости
- **Секреты (`.env`)** → хранить в менеджере паролей

## Почему такая конфигурация

Весь workload I/O-bound (Telegram API, DeepSeek API, Google Embeddings API) — CPU не является узким местом. ChromaDB требует SSD для random I/O по индексу. 2 GB RAM покрывает все четыре Docker-сервиса с запасом.
