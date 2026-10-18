from pyspark.sql import SparkSession
from pyspark.sql import functions as F

spark = SparkSession.builder.appName("hello-cluster").getOrCreate()

# Transformations : rien ne s'exécute encore (lazy evaluation)
df = spark.range(0, 10_000_000).withColumn("bucket", F.col("id") % 10)
result = df.groupBy("bucket").count().orderBy("bucket")

# Action : c'est ici que Spark lance réellement le travail
result.show()

print("Nombre de partitions :", df.rdd.getNumPartitions())
input("Va voir http://localhost:4040 puis appuie sur Entrée pour terminer...")
spark.stop()