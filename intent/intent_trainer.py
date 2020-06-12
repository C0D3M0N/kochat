"""
@author : Hyunwoong
@when : 5/9/2020
@homepage : https://github.com/gusdnd852
"""
import os

import torch
from torch import nn
from torch.optim import Adam

from config import Config
from util.dataset import Dataset
from util.graph_drawer import GraphDrawer


class IntentTrainer:
    train_data, test_data = None, None
    conf = Config()
    data = Dataset()

    def __init__(self, embed, model):
        self.embed = embed
        self.model = model.Model().to(self.conf.device)
        self.initialize_weights(self.model)
        self.loss = nn.CrossEntropyLoss()
        self.load_dataset(embed)
        self.optimizer = Adam(
            lr=self.conf.intent_lr,
            params=self.model.parameters(),
            weight_decay=self.conf.intent_weight_decay)

    def load_dataset(self, embed):
        self.train_data, self.test_data = \
            self.data.intent_train(embed, self.conf.intent_datapath)

    def train(self):
        errs, accs = [], []
        print("INTENT : START TRAIN !")
        for i in range(self.conf.intent_epochs):
            err, acc = self.__train_epoch(self.model, self.train_data)
            accs.append(acc)
            errs.append(err)

            self.print_log(i, err, acc)
            self.save_result('accuracy', accs)
            self.save_result('error', errs)

        drawer = GraphDrawer()
        drawer.draw('accuracy', 'red')
        drawer.draw('error', 'blue')

        if not os.path.exists(self.conf.intent_storepath):
            os.makedirs(self.conf.intent_storepath)

        torch.save(self.model.state_dict(), self.conf.intent_storefile)

    def test(self):
        print("test start ...")
        self.model.load_state_dict(torch.load(self.conf.intent_storefile))
        self.model.eval()

        test_feature, test_label = self.test_data
        x = test_feature.float().cuda()
        y = test_label.long().cuda()
        y_ = self.model(x.permute(0, 2, 1)).float()
        y_ = self.model.out(y_.squeeze())

        _, predict = torch.max(y_, dim=1)
        acc = self.get_accuracy(y, predict)
        print("test accuracy is {}".format(acc))

    def __train_epoch(self, model, train_set):
        errors, accuracies = [], []
        for train_feature, train_label in train_set:
            x = train_feature.float().cuda()
            y = train_label.long().cuda()
            y_ = self.model(x.permute(0, 2, 1)).float()
            y_ = self.model.out(y_.squeeze())

            self.optimizer.zero_grad()
            error = self.loss(y_, y)
            error.backward()
            self.optimizer.step()

            errors.append(error.item())
            _, predict = torch.max(y_, dim=1)

            acc = self.get_accuracy(y, predict)
            accuracies.append(acc)

        error = sum(errors) / len(errors)
        accuracy = sum(accuracies) / len(accuracies)
        return error, accuracy

    def print_log(self, step, train_err, train_acc):
        p = self.conf.intent_log_precision
        print('step : {0} , train_error : {1} , train_acc : {2}'
              .format(step, round(train_err, p), round(train_acc, p)))

    def save_result(self, file_name, result):
        f = open(self.conf.root_path + '/log/{0}.txt'.format(file_name), 'w')
        f.write(str(result))
        f.close()

    @staticmethod
    def initialize_weights(model):
        if hasattr(model, 'weight') and model.weight.dim() > 1:
            nn.init.kaiming_uniform(model.weight.data)

    @staticmethod
    def get_accuracy(predict, label):
        all, correct = 0, 0
        for i in zip(predict, label):
            all += 1
            if i[0] == i[1]:
                correct += 1
        return correct / all
