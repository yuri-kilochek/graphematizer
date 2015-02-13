import os
import os.path
import subprocess
import argparse
import collections
import itertools
import time
import sys

GRAPHEMATIZER_PATH = os.path.normpath('../graphematizer')
TERMINAL_WIDTH = 80

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('test_set', help='Test set to run.')
arg_parser.add_argument('-c', '--concurrency', type=int, default=(os.cpu_count() or 4)**3,
                        help='Max amount of tests to run concurrently.'
                             ' Defaults to CPU count cubed or 16 if is is unavailable.')
arg_parser.add_argument('-t', '--score_threshold', type=float, default=0.0,
                        help='If a test scores below this value it will be shown. Default to 0.0, showing no tests.')
args = arg_parser.parse_args()


def lcs_len(a, b):
    m = len(a)
    n = len(b)
    c = [[0] * (n + 1)] * (m + 1)
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                c[i][j] = c[i - 1][j - 1] + 1
            else:
                c[i][j] = max(c[i][j - 1], c[i - 1][j])
    return c[m][n]


def load_graphemes(graphemes_pathname):
    with open(graphemes_pathname, 'r', encoding='utf-8') as file:
        return [g.rstrip() for g in file.readlines()]


class Tester:
    def __init__(self, test_id):
        self._test_id = test_id

        plaintext_path = os.path.join(args.test_set, 'tests', os.path.join(*test_id), 'plaintext.txt')
        self._true_graphemes_path = os.path.join(args.test_set, 'tests', os.path.join(*test_id), 'graphemes.txt')
        self._test_graphemes_path = '~{}-{}-graphemes.txt'.format(args.test_set, '-'.join(test_id))

        self._process = subprocess.Popen([GRAPHEMATIZER_PATH,
                                         os.path.relpath(plaintext_path, GRAPHEMATIZER_PATH),
                                         os.path.relpath(self._test_graphemes_path, GRAPHEMATIZER_PATH)])

        self._result = None

    @property
    def result(self):
        if self._result is None:
            self._process.poll()

            if self._process.returncode is None:
                return None

            if self._process.returncode != 0:
                raise Exception('Test {} is bad.'.format('/'.join(self._test_id)))

            true_graphemes = load_graphemes(self._true_graphemes_path)
            test_graphemes = load_graphemes(self._test_graphemes_path)

            os.remove(self._test_graphemes_path)

            total = len(true_graphemes)
            match = lcs_len([g[2:] for g in true_graphemes], [g[2:] for g in test_graphemes])
            match_marked = lcs_len(true_graphemes, test_graphemes)

            self._result = self._test_id, total, match, match_marked

        return self._result


def enumerate_tests():
    def enumerate_tests(path, test_id):
        for _, dirs, files in os.walk(path):
            if 'plaintext.txt' in files:
                yield test_id
            else:
                for dir in dirs:
                    yield from enumerate_tests(os.path.join(path, dir), test_id + [dir])
            break
    yield from enumerate_tests(os.path.join(args.test_set, 'tests'), [])


def do_tests():
    testers = collections.deque()

    test_ids = iter(enumerate_tests())
    while True:
        while testers and testers[0].result is not None:
            yield testers.popleft().result

        active_count = 0
        for tester in testers:
            if tester.result is None:
                active_count += 1

        if active_count < args.concurrency:
            next_id = next(test_ids, None)
            if next_id is None:
                break
            testers.append(Tester(next_id))
        else:
            time.sleep(sys.float_info.epsilon)

    while testers:
        if testers[0].result is not None:
            yield testers.popleft().result
        else:
            time.sleep(sys.float_info.epsilon)


def compute_scores(total, match, match_marked):
    if total > 0:
        return match / total, match_marked / total
    else:
        return 1.0, 1.0


total = 0
match = 0
match_marked = 0

print('bad tests (with score below {}):'.format(args.score_threshold))
print(' {:>14} |  {:>14} | {}'.format('score', 'score marked', 'id'))
for i, (i_id, i_total, i_match, i_match_marked) in enumerate(do_tests()):
    i_score, i_score_marked = compute_scores(i_total, i_match, i_match_marked)

    if i_score < args.score_threshold or i_score_marked < args.score_threshold:
        text = '{:>14.3f}% | {:>14.3f}% | {}'.format(i_score * 100, i_score_marked * 100, '/'.join(i_id))
        print(text, end=' ' * (TERMINAL_WIDTH - 1 - len(text)) + '\n')

    total += i_total
    match += i_match; match_marked += i_match_marked

    score, score_marked = compute_scores(total, match, match_marked)
    text = '{:>14.3f}% | {:>14.3f}% | <total over {} tests>'.format(score * 100, score_marked * 100, i)
    print(text, end=' ' * (TERMINAL_WIDTH - 1 - len(text)) + '\r')

print()
print('Done.')
