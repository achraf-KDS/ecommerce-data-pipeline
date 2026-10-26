from pyspark.sql import SparkSession
from pyspark.sql import functions as F

spark = SparkSession.builder.appName("inspect-landing").getOrCreate()
spark.sparkContext.setLogLevel("WARN")

events = spark.read.json("/opt/project/data/landing/events/")

events.printSchema()
print("Nombre d'événements :", events.count())

events.groupBy("event_type").count().orderBy(F.desc("count")).show()
events.groupBy("device").count().orderBy(F.desc("count")).show()

spark.stop()