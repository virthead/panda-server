import re
import datetime

import optparse

from pandaserver.taskbuffer.OraDBProxy import DBProxy
from pandaserver.config import panda_config
import pandaserver.userinterface.Client as Client

usage = "%prog [options] siteName"
optP = optparse.OptionParser(usage=usage,conflict_handler="resolve")
optP.add_option('--assigned',action='store_const',const=True,dest='assigned',
                default=False,help='reassign jobs in assigned state. Jobs in activated state are reassigned by default')
optP.add_option('--olderThan',action='store',dest='olderThan',default=1,help="reassign jobs with modificationTime older than N hours (1 by default)")
options,args = optP.parse_args()

# password

proxyS = DBProxy()
proxyS.connect(panda_config.dbhost,panda_config.dbpasswd,panda_config.dbuser,panda_config.dbname)

site = args[0]

try:
    options.olderThan = int(options.olderThan)
except Exception:
    pass
timeLimit = datetime.datetime.utcnow() - datetime.timedelta(hours=options.olderThan)
varMap = {}
if options.assigned:
    varMap[':jobStatus']        = 'assigned'
else:
    varMap[':jobStatus']        = 'activated'
varMap[':modificationTime'] = timeLimit
varMap[':prodSourceLabel']  = 'managed'
varMap[':computingSite']    = site
if options.assigned:
    sql = "SELECT PandaID,lockedby FROM ATLAS_PANDA.jobsDefined4 "
else:
    sql = "SELECT PandaID,lockedby FROM ATLAS_PANDA.jobsActive4 "
sql += "WHERE jobStatus=:jobStatus AND computingSite=:computingSite AND modificationTime<:modificationTime AND prodSourceLabel=:prodSourceLabel ORDER BY PandaID"
status,res = proxyS.querySQLS(sql,varMap)

print("got {0} jobs".format(len(res)))

jobs = []
jediJobs = []
if res is not None:
    for (id,lockedby) in res:
        if lockedby == 'jedi':
            jediJobs.append(id)
        else:
            jobs.append(id)
if len(jobs):
    nJob = 100
    iJob = 0
    while iJob < len(jobs):
        print('reassign  %s' % str(jobs[iJob:iJob+nJob]))
        Client.reassignJobs(jobs[iJob:iJob+nJob])
        iJob += nJob
if len(jediJobs) != 0:
    nJob = 100
    iJob = 0
    while iJob < len(jediJobs):
        print('kill JEDI jobs %s' % str(jediJobs[iJob:iJob+nJob]))
        Client.killJobs(jediJobs[iJob:iJob+nJob],51)
        iJob += nJob
