from pymongo import MongoClient

client = MongoClient('localhost', 27017)

seesaw_collection = client.Simulations.SeeSaw

data = {"teste":"insert"}

h = 0.01
d = int(f'{h:e}'.split('e')[-1])*-1

print(d)

