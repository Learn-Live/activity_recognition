import os
import time
from collections import Counter, OrderedDict
from itertools import zip_longest

import matplotlib.pyplot as plt
import numpy as np
import sklearn
from scipy.stats import norm
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KernelDensity
from sklearn.tree import DecisionTreeClassifier

import generate


class AnomalyDetector:

    def __init__(self, model_name='GMM', model_parameters= {}, random_state=42):
        self.model_name = model_name
        self.random_state = random_state
        self.model_parameters = model_parameters

    def fit(self, X_train, y_train=None):
        # 1. preprocessing
        # 2. build model
        if self.model_name == 'KDE':
            self.model = KernelDensity(kernel='gaussian', bandwidth=0.5)
            self.model.fit(X_train)
        elif self.model_name =='GMM':
            pass
        elif self.model_name == 'DT':
            self.model = DecisionTreeClassifier(random_state=self.random_state)
            self.model.fit(X_train, y_train)
        elif self.model_name == 'RF':
            n_estimators = self.model_parameters['n_estimators']
            self.model = RandomForestClassifier(n_estimators, random_state=self.random_state)
            self.model.fit(X_train, y_train)
        elif self.model_name == 'SVM':
            kernel = self.model_parameters['kernel']
            self.model = sklearn.svm.SVC(kernel=kernel, random_state=self.random_state)
            self.model.fit(X_train, y_train)


    def get_threshold(self, X_train, q=0.95):
        # 3. anomaly theadhold: t
        log_dens = self.model.score_samples(X_train)
        self.thres = np.quantile(np.exp(log_dens), q=q)

    def predict_prob(self, X):
        log_dens = self.model.score_samples(X)

        return np.exp(log_dens)

    def predict(self, X):
        dens = self.predict_prob(X)
        dens[dens < self.thres] = 1
        dens[dens >= self.thres] = 0

        return dens


def generate_data(in_dir ='out/output_mp4', out_file = 'out/Xy.dat'):
    if type(in_dir) == str:
        in_dir = [in_dir]
    elif type(in_dir) == list:
        pass
    else:
        raise NotImplementedError()

    meta = generate.form_X_y(in_dir)
    generate.dump_data(meta, out_file)
    return meta

def get_video_data(in_dir = ['out/camera1_mp4']):
    mp = OrderedDict()
    i = 0
    c = 0
    X = []
    Y = []
    for _in_dir in in_dir:
        for f in sorted(os.listdir(_in_dir)):
            pth = os.path.join(_in_dir, f)
            y = generate.extract_label(f)
            if y == 'no_interaction' or '.txt' in pth: continue
            if y not in mp.keys():
                mp[y] = (i, 1)  # (idx, cnt)
                i += 1
            else:
                mp[y] = (mp[y][0], mp[y][1] + 1)
            X.append(pth)
            Y.append(mp[y][0])
            c += 1
    print(f'{in_dir}: total videos: {c}, and classes: {i}')
    print(f'{in_dir}: Labels: {mp.items()}')
    mp2 = {v[0]:k for k, v in mp.items()}
    meta = {'X': X, 'y': Y, 'shape': (c, ), 'label2idx': mp, 'idx2label': mp2, 'in_dir': in_dir}
    return meta

def augment_data(files, labels, idx2label, augment = True):
    mp = OrderedDict()
    i = 0
    c = 0
    video_id = []
    X = []
    Y = []
    for pth, y in zip(files, labels):
        # print(pth, y)
        if augment:
            xs = generate.extract_feature2(pth)
        else:
            xs = generate.extract_feature3(pth)
        name = idx2label[y]
        if name == 'no_interaction': continue
        if name not in mp.keys():
            mp[name] = (y, len(xs))  # (idx, cnt)
        else:
            mp[name] = (mp[name][0], mp[name][1] + 1)
        video_id.extend([pth]*len(xs))
        X.extend(xs)
        Y.extend([mp[name][0]] * len(xs))
        c += 1
    print(f'total videos: {len(X)}, and classes: {len(mp.keys())}')
    print(f'Labels: {mp.items()}')
    X = np.asarray(X)
    Y = np.asarray(Y)
    meta = {'X': X, 'y': Y, 'shape': (c, len(X[0])), 'label2idx': mp, 'idx2label': idx2label, 'in_dir': ''}
    return video_id, X, Y, meta


def main(random_state = 42):
    # split train and test set for vides data
    meta = get_video_data(in_dir = ['out/camera1_mp4'])
    X_train, X_test, y_train, y_test = train_test_split(meta['X'], meta['y'], test_size=0.3, random_state=random_state)
    mp = meta['idx2label']

    # augment train set by sliding window
    video_id_train, X_train, y_train, meta_train = augment_data(X_train, y_train, mp, augment=True)
    video_id_test, X_test, y_test, meta_test = augment_data(X_test, y_test, mp, augment= False)

    # # in_file = 'out/Xy-mp4.dat'
    # # in_file = 'out/Xy-mkv.dat'
    # in_file = 'out/Xy-comb.dat'
    # if not os.path.exists(in_file):
    #     if 'mkv' in in_file:
    #         in_dir = 'out/output_mkv'
    #         out_file = 'out/Xy-mkv.dat'
    #     elif 'mp4' in in_file:
    #         in_dir = 'out/output_mp4'
    #         out_file = 'out/Xy-mp4.dat'
    #     elif 'comb' in in_file:
    #         in_dir = ['out/output_mp4', 'out/output_mkv']
    #         out_file = 'out/Xy-comb.dat'
    #     else:
    #         raise NotImplementedError
    #     generate_data(in_dir, out_file)
    # meta = generate.load_data(in_file)
    # X, y = meta['X'], meta['y']
    # print(meta['in_dir'], ', its shape:', meta['shape'])
    # print(f'mapping-(activity:(label, cnt)): ', '\n\t' + '\n\t'.join([f'{k}:{v}' for k, v in meta['labels'].items()]))
    # mp = {v[0]: k for k, v in meta['labels'].items()}  # idx -> activity name
    # X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=random_state)
    # print(f'X_train: {X_train.shape}\nX_test: {X_test.shape}')
    # print(X_train[:10])

    res = []
    for n_estimators in [10, 50, 100, 200, 300, 400, 500, 700, 900, 1000]:
        print(f'\nn_estimators: {n_estimators}')
        # 2. build the kde model
        # detector = AnomalyDetector(model_name='KDE', model_parameters = {'bandwidth': 0.1, 'kernel': 'gussisan'})
        # detector = AnomalyDetector(model_name='DT', model_parameters={}, random_state=random_state)
        # detector = AnomalyDetector(model_name='RF', model_parameters={'n_estimators':n_estimators}, random_state=random_state)
        # detector = AnomalyDetector(model_name='SVM', model_parameters={'kernel':'rbf'}, random_state=random_state)
        detector = AnomalyDetector(model_name='SVM', model_parameters={'kernel':'linear'}, random_state=random_state)
        detector.fit(X_train, y_train)
        #
        # # 3. compute the threshold
        # detector.get_threshold(X_train, q=0.01)
        # # print(detector.predict_prob(X_train))


        # 4. evaulation
        y_preds = detector.model.predict(X_test)
        # y_preds = []
        # X_test = np.asarray(X_test)[:, np.newaxis]
        #
        # for i, x in enumerate(X_test):
        #     # time.sleep(1)
        #     y_prob = detector.predict_prob(x).item()
        #     # y_pred = detector.predict(x).item()
        #     if y_prob < detector.thres:
        #         print(f'{i}, x: {x}-> ***novelty')
        #         y_pred = 1
        #     else:
        #         print(f'{i}, x: {x}-> normal ')
        #         y_pred = 0
        #     y_preds.append(y_pred)

        print('y_test (label, cnt): ', sorted(Counter(y_test).items(), key=lambda x:x[0]))
        acc = sklearn.metrics.accuracy_score(y_test, y_preds)
        print(f'accuracy: {acc}')
        res.append((acc, n_estimators))
        cm = sklearn.metrics.confusion_matrix(y_test, y_preds)
        # print(cm)
        # labels = list(mp.keys())
        w = 15   # width
        # print()
        labels = [f'{v[:w]:<{w}}' for k,v in mp.items()]
        # for v in zip_longest(*labels, fillvalue=' '):
        #     print(' '.join(v))
        # print(' '* 15 + ' '.join(labels)+f'(predicted)')
        print(' '* 40 + '(predicted)')
        print(' '*(w+1)  + '\t' + '\t\t'.join([f'({k})' for k, v in mp.items()]))
        for i,vs in enumerate(list(cm)):
            print(f'{mp[i][:w]:<{w}} ({i})\t', '\t\t'.join([f'{v}' for v in list(vs)]))


        # 5 get misclassification
        err_mp = {}
        for v_id, y_t, y_p in zip(video_id_test, y_test, y_preds):
            if y_t != y_p:
                name = f'{mp[y_t]}({y_t}):{v_id}'
                if name not in err_mp.keys():
                    err_mp[name] = [f'{mp[y_p]}({y_p})']
                else:
                    err_mp[name].append(f'{mp[y_p]}({y_p})')

                # print(f'{mp[y_t]} -> {mp[y_p]}')
        print('***misclassified classes:')
        print('\t'+'\n\t'.join([ f'{k}->{Counter(vs)}' for k, vs in err_mp.items()]))
    print(res)

if __name__ == '__main__':
    main()