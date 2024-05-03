# from subprocess import Popen
# from stdlib.utility import get_cursor,inactive_inDB
# import time
# from random import randint

# def main():
#     try:
#         cursor,cnx=get_cursor("order_acceptance")
#         #cnx.execute("""SELECT userid FROM `AMO` where status = 'Active'""")
#         #cnx.execute("""SELECT userid FROM `AMO` where userid = '245559'""")
#         cnx.execute("""SELECT userid FROM `AMO` where status = 'Active' and Client_name like 'KSH-Ri%'""")
#         userid=cnx.fetchall()
#         print(f"Total Active Account = {len(userid)}")
#         for uid in userid:
#             print(uid['userid'])
#             command = ['python', '-m', 'main.amo',uid['userid'],"amo"]
#             random_sleep_time = randint(4,5)
#             process = Popen(command)
#             time.sleep(random_sleep_time)
#     except Exception as ex:
#          print(ex)
# if __name__ == "__main__":
#     main()
    
from main.amo import main
if __name__ == "__main__":
    main() 