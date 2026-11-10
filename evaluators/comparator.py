from math import *
from decimal import Decimal
import numpy as np
 
# Using code from https://github.com/saimadhu-polamuri/DataAspirant_codes/tree/master/Similarity_measures
def euclidean_distance(x,y):

    """ return euclidean distance between two lists """

    return sqrt(sum(pow(a-b,2) for a, b in zip(x, y)))

def manhattan_distance(x,y):

    """ return manhattan distance between two lists """

    return sum(abs(a-b) for a,b in zip(x,y))

def minkowski_distance(x,y,p_value):

    """ return minkowski distance between two lists """

    return nth_root(sum(pow(abs(a-b),p_value) for a,b in zip(x, y)),
        p_value)

def nth_root(value, n_root):

    """ returns the n_root of an value """

    root_value = 1/float(n_root)
    return round (Decimal(value) ** Decimal(root_value),3)

def cosine_similarity(x,y):

    """ return cosine similarity between two lists """

    numerator = sum(a*b for a,b in zip(x,y))
    denominator = square_rooted(x)*square_rooted(y)
    return round(numerator/float(denominator),3)

def square_rooted(x):

    """ return 3 rounded square rooted value """

    return round(sqrt(sum([a*a for a in x])),3)

def jaccard_similarity(x,y):
    """ returns the jaccard similarity between two lists """
    intersection_cardinality = len(set.intersection(*[set(x), set(y)]))
    union_cardinality = len(set.union(*[set(x), set(y)]))
    return intersection_cardinality/float(union_cardinality)


def rbo(list1, list2, p=0.9):
    # TODO: Implement
    return 0.0

def word_err_rate(x, y):
    """ return word error rate (WER) for reference and hypothesis transcripts """
    reference, hypothesis = x.split(), y.split()
    row = list(range(len(hypothesis) + 1))
    for i, word in enumerate(reference, 1):
        previous, row = row, [i] + [0] * len(hypothesis)
        for j, candidate in enumerate(hypothesis, 1):
            row[j] = min(row[j - 1] + 1, previous[j] + 1,
                         previous[j - 1] + (word != candidate))
    return row[-1] / len(reference)


def character_err_rate(x, y):
    """ return character error rate (CER) for reference and hypothesis transcripts """
    row = list(range(len(y) + 1))
    for i, character in enumerate(x, 1):
        previous, row = row, [i] + [0] * len(y)
        for j, candidate in enumerate(y, 1):
            row[j] = min(row[j - 1] + 1, previous[j] + 1,
                         previous[j - 1] + (character != candidate))
    return row[-1] / len(x)


def percentage_corr_kekpoints(x, y, scale, ptrhld=0.2):
    """ return PCK using the provided scale and threshold proportion """
    distances = np.linalg.norm(np.asarray(x)[:, :2] - np.asarray(y)[:, :2], axis=1)
    return float(np.mean(distances <= ptrhld * scale) * 100)
