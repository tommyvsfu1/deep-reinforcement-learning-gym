from scipy.stats import truncnorm
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

seed = 11037
np.random.seed(seed)
torch.manual_seed(seed)
torch.cuda.manual_seed_all(seed)

def hidden_init(layer):
    fan_in = layer.bias.data.size()[0]
    lim = 1. / np.sqrt(fan_in)
    return (-lim, lim)


def truncated_normal_(tensor, mean=0, std=0.01):
    # https://discuss.pytorch.org/t/implementing-truncated-normal-initializer/4778/20
    size = tensor.shape
    tmp = tensor.new_empty(size + (4,)).normal_()
    valid = (tmp < 2) & (tmp > -2)
    ind = valid.max(-1, keepdim=True)[1]
    tensor.data.copy_(tmp.gather(-1, ind).squeeze(-1))
    tensor.data.mul_(std).add_(mean)
    return tensor


class MLP(nn.Module):
    """
    Input : (state_dim, action_num, hidden_dim)
    Output : action_prob : (N,action_dim)
    """
    def __init__(self, state_dim, action_num, hidden_dim):
        super(MLP, self).__init__()
        self.action_layer = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            torch.nn.Dropout(0.5), 
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            torch.nn.Dropout(0.5),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_num),
            nn.LogSoftmax(dim=-1)
        )

    def forward(self, x):
        action_prob = self.action_layer(x)
        action_prob = torch.exp(action_prob)
        return action_prob


class Actor(nn.Module):   # ae(s)=a
    def __init__(self,s_dim,action_size, fc1_units=256, fc2_units=256):
        super(Actor,self).__init__()
        self.fc1 = nn.Linear(s_dim, fc1_units)
        self.fc2 = nn.Linear(fc1_units, fc2_units)
        self.fc3 = nn.Linear(fc2_units, action_size)
        self.reset_parameters()

    def reset_parameters(self):
        with torch.no_grad():
            self.fc1.bias.copy_(torch.tensor([0.03]))
            self.fc2.bias.copy_(torch.tensor([0.03]))
            self.fc3.bias.copy_(torch.tensor([0.03]))
            
        # self.fc1.weight.data.uniform_(*hidden_init(self.fc1))
        # self.fc2.weight.data.uniform_(*hidden_init(self.fc2))
        # self.fc3.weight.data.uniform_(*hidden_init(self.fc3))

    def forward(self, state):
        """Build an actor (policy) network that maps states -> actions."""
        # x = F.relu(self.bn1(self.fc1(state)))
        x = F.relu(self.fc1(state))
        x = F.relu(self.fc2(x))
        return torch.tanh(self.fc3(x)) * 2

class Critic(nn.Module):   # ae(s)=a
    def __init__(self,state_size,action_size, fcs1_units=256, fc2_units=256):
        super(Critic,self).__init__()
        self.fcs1 = nn.Linear(state_size, fcs1_units)
        self.bn1 = nn.BatchNorm1d(fcs1_units)
        self.fca2 = nn.Linear(action_size, fc2_units)
        self.bn2 = nn.BatchNorm1d(fc2_units)
        self.fc2 = nn.Linear(fcs1_units+action_size, fc2_units)

        self.fc3 = nn.Linear(fc2_units, 1)
        self.reset_parameters()

    def reset_parameters(self):
        with torch.no_grad():
            self.fcs1.bias.copy_(torch.tensor([0.03]))
            self.fca2.bias.copy_(torch.tensor([0.03]))
            self.fc2.bias.copy_(torch.tensor([0.03]))
            self.fc3.bias.copy_(torch.tensor([0.03]))

        # self.fcs1.weight.data.uniform_(*hidden_init(self.fcs1))
        # self.fc2.weight.data.uniform_(*hidden_init(self.fc2))
        # self.fc3.weight.data.uniform_(-3e-3, 3e-3)

    def forward(self, xs):
        """Build a critic (value) network that maps (state, action) pairs -> Q-values."""
        state, action = xs
        s = self.fcs1(state)
        # a = self.fca2(action)
        # h2 = F.relu( self.bn2(s+a) )
        # h3 = self.fc3(h2)
        x = torch.cat((s, action), dim=1)
        x = F.relu(self.fc2(x))
        x = self.fc3(x)
        return x


# ac = Critic(2,2)
# action = torch.ones((16,2))
# state = torch.ones((16,2))
# o = ac((state, action))

# target = torch.ones((16,1))
# loss_fn = torch.nn.MSELoss()
# y = loss_fn(o, target)
# y.backward()
# for p in ac.named_parameters():
#     layer_name, parameter = p
#     print("layer name: ", layer_name)
#     if layer_name[0:2] != "bn":
#         norm = torch.norm(parameter.grad)
#         print("norm", norm)