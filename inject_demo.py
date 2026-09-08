import sqlite3

conn = sqlite3.connect("knowledge_layer.db")
cursor = conn.cursor()

# Insert Fact A from Document 1
cursor.execute("""
INSERT INTO facts (category, entity, metric_or_attribute, value, context, source_sentence, source_filename, page_number)
VALUES ('Financial', 'Delhivery', 'Demo Cross-Check Revenue', '₹5,000 Cr', 'FY21 Standalone', 'Standalone revenue was ₹5,000 Cr.', '01-delhivery-prospectus-2022-excerpt.pdf', 1)
""")

# Insert Fact B from Document 2
cursor.execute("""
INSERT INTO facts (category, entity, metric_or_attribute, value, context, source_sentence, source_filename, page_number)
VALUES ('Financial', 'Delhivery', 'Demo Cross-Check Revenue', '₹7,200 Cr', 'FY22 Consolidated', 'Consolidated revenue reached ₹7,200 Cr.', '02-delhivery-annual-report-fy24-excerpt.pdf', 2)
""")

conn.commit()
conn.close()
print("✅ Guaranteed demo cluster injected! Return to the UI and click 'Run Analysis'.")