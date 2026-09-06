from alembic.config import Config
c = Config('D:/CBA 4.0/Festivales/Back/alembic.ini')
from alembic import command

print("Heads:")
heads = command.heads(c)
for h in heads:
    print(f"  {h}")

print("\nUpgrade head...")
command.upgrade(c, 'head')
print("Upgrade completed successfully!")