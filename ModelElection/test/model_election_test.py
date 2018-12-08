from ModelElection.ModelElection import *
import pytest
import sys

def test_simple():
    e = Election('Test title')
    assert str(e) == '<Test title: >'
    con = Contest('Contest 1')
    assert str(con) == '<Contest 1: >'
    ch = Choice('Choice 1.1')
    con.add(ch)
    assert str(ch) == '<Choice: Choice 1.1>'
    ch = Choice('Choice 1.2')
    con.add(ch)
    e.add(con)
    chl2 = (Choice('Choice2.1'), Choice('Choice2.2'))
    chl3 = [Choice('Choice3.1'), Choice('Choice3.2')]
    con2 = Contest('Contest 2')
    con2.add(chl2)
    con3 = Contest('Contest 3')
    con3.add(chl3)
    e.add((con2, con3))
    assert str(e) == '<Test title: <Contest 1: <Choice: Choice 1.1>, <Choice: Choice 1.2>>, ' \
                     '<Contest 2: <Choice: Choice2.1>, <Choice: Choice2.2>>, ' \
                     '<Contest 3: <Choice: Choice3.1>, <Choice: Choice3.2>>>'
    assert [str(x) for x in con2] == ['<Choice: Choice2.1>', '<Choice: Choice2.2>']
    assert [str(x) for x in e] == ['<Contest 1: <Choice: Choice 1.1>, <Choice: Choice 1.2>>',
                                   '<Contest 2: <Choice: Choice2.1>, <Choice: Choice2.2>>',
                                   '<Contest 3: <Choice: Choice3.1>, <Choice: Choice3.2>>']


def test_real_world(capsys):
    # test with real-world data
    #
    with open('test/hard_matches.tsv') as hardm:
        hm = hardmatches(hardm)

    e = Election('Humboldt County June 2018')
    e.load('test/ElectionModel.txt')

    for ocr_pair in open('test/ocr_out.tsv').readlines():
        pair = ocr_pair.split('\t')
        assert len(pair) == 2
        ocr_contest, ocr_choice = (preprocess(x) for x in pair)
        contest = e.fuzmatch(ocr_contest)
        if contest:
            choice = contest.fuzmatch(ocr_choice)
            if choice:
                print '{}: {}'.format(contest.name, choice.name)
            else:
                print pair[1]
                hardmatch = hm.match(pair[1].strip())        # non-preprocessed version
                if hardmatch:
                    print '{}: {} (hard match)'.format(contest.name, hardmatch)
                else:
                    sys.stderr.write('Choice not found in {} {}\n'.format(contest.name, pair))
        else:
                sys.stderr.write( 'unrecognized contest: {}\n'.format(pair))

    out, err = capsys.readouterr()
    with open('test/test_real_world_stdout.txt') as stdoutdata:
        assert out == stdoutdata.read()
    with open('test/test_real_world_stderr.txt') as stderrdata:
        assert err == stderrdata.read()
