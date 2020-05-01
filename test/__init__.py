from test.integrationtests.skills.skill_tester import SkillTest

import mock
import datetime

def test_runner(skill, example, emitter, loader):

    processedFeed = {
        'episodes': {},
        'totalCnt': 5,
        'airingTodayCnt': 1,
        'updatedAt': datetime.datetime.now().date()
    }

    s = [s for s in loader.skills if s and s.root_dir == skill]
    s[0].myepisodes = mock.MagicMock()
    s[0].myepisodes.processFeed.return_value = processedFeed
    return SkillTest(skill, example, emitter).run(loader)
