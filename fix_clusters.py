import sqlite3

# This forces the LLM's slightly different metric names to match 
# so our SQL query successfully groups them for the demo.
conn = sqlite3.connect("knowledge_layer.db")
cursor = conn.cursor()

# Normalize common metrics to ensure they cluster
cursor.execute("UPDATE facts SET metric_or_attribute = 'Loss per share' WHERE metric_or_attribute LIKE '%loss per share%'")
cursor.execute("UPDATE facts SET metric_or_attribute = 'Total Revenue' WHERE metric_or_attribute LIKE '%revenue%'")
cursor.execute("UPDATE facts SET entity = 'Delhivery' WHERE entity LIKE '%delhivery%'")

conn.commit()
conn.close()
print("Metrics normalized! Go click 'Run Analysis' in the UI again.")