# generates driver/executor logs + a tiny job
logger = sc._jvm.org.apache.log4j.LogManager.getLogger("demo.logger")
logger.info("hello from Fabric")
sc.parallelize(range(1000)).count()
