from connector import ConnectionThread
from controller import SDControl
import queue

machines = ["192.168.1.195","thinkd.local", "thinkc.local",] #

# the queues are shared between connector and controller
workQueue = queue.Queue()
talkQueue = queue.Queue()
pingQueue = queue.Queue()

# change the list of machine names to a list of connected machines; start the machines too!
for i in range(len(machines)):
    machines[i] = ConnectionThread(i, machines[i], workQueue, talkQueue, pingQueue)
# start the controller; open the window...
controller = SDControl(machines,workQueue,talkQueue,pingQueue)

# controller.statuscode[0].insert("1.0","status\n a") # line 1 position 0
# controller.statuscode[1].insert("1.0","status\n b")
# controller.statuscode[2].insert("1.0","status\n c")

### the main task loop ###
controller.root.mainloop()

controller.exit()
print("done.")

