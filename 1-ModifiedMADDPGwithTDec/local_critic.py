
import numpy as np
import torch as T
import torch.nn.functional as F
from Classes.networks import ActorNetwork, CriticNetwork

class Agent():
    def __init__(self, alpha, beta, input_dims, tau, n_actions, gamma, C_fc1_dims, C_fc2_dims, A_fc1_dims,
                 A_fc2_dims, batch_size, n_agents, agent_name, noise):
        self.gamma = gamma
        self.tau = tau
        self.batch_size = batch_size
        self.alpha = alpha
        self.beta = beta
        self.number_agents = n_agents
        self.number_actions = n_actions
        self.number_states = input_dims
        self.agent_name = agent_name
        self.noise = noise

        # [RQ1-CMDP] constraint bookkeeping (set from Main.py)
        self.constraint_mode = 'soft'   # 'soft' (reward penalty) or 'hard' (CMDP)
        self.cost_source = 'critic'     # [RQ1-CMDP A1] 'critic' (learned Q^c, ours) or 'raw' (RCPO reward-folded)
        self.lam = 0.0                  # per-platoon Lagrange multiplier lambda_j
        # [RQ1-CMDP] per-episode training diagnostics (reset + read by Main.py):
        #   diag_closs_sum/diag_n  -> Bellman MSE of the cost critic (is Q^c converging?)
        #   diag_force_sum/diag_n  -> lam_j * mean Q^c(s, pi(s)) (the constraint force on the actor)
        self.diag_closs_sum = 0.0
        self.diag_force_sum = 0.0
        self.diag_n = 0

        self.actor = ActorNetwork(alpha, input_dims, A_fc1_dims, A_fc2_dims, n_agents,
                                n_actions=n_actions, name='actor', agent_label=agent_name)
        self.critic_task1 = CriticNetwork(beta, input_dims, C_fc1_dims, C_fc2_dims, n_agents,
                                n_actions=n_actions, name='critic_task1', agent_label=agent_name)

        self.critic_task2 = CriticNetwork(beta, input_dims, C_fc1_dims, C_fc2_dims, n_agents,
                                          n_actions=n_actions, name='critic_task2', agent_label=agent_name)

        # [RQ1-CMDP] per-platoon cost critic: predicts expected discounted
        # AoI-violation count for this platoon (same shape as a task critic).
        self.critic_cost = CriticNetwork(beta, input_dims, C_fc1_dims, C_fc2_dims, n_agents,
                                         n_actions=n_actions, name='critic_cost', agent_label=agent_name)

        self.target_actor = ActorNetwork(alpha, input_dims, A_fc1_dims, A_fc2_dims, n_agents,
                                n_actions=n_actions, name='target_actor', agent_label=agent_name)

        self.target_critic_task1 = CriticNetwork(beta, input_dims, C_fc1_dims, C_fc2_dims, n_agents,
                                n_actions=n_actions, name='target_critic_task1', agent_label=agent_name)

        self.target_critic_task2 = CriticNetwork(beta, input_dims, C_fc1_dims, C_fc2_dims, n_agents,
                                                 n_actions=n_actions, name='target_critic_task2', agent_label=agent_name)

        self.target_critic_cost = CriticNetwork(beta, input_dims, C_fc1_dims, C_fc2_dims, n_agents,
                                                n_actions=n_actions, name='target_critic_cost', agent_label=agent_name)

        self.update_network_parameters(tau=1)

    def choose_action(self, observation):
        self.actor.eval()
        state = T.tensor([observation], dtype=T.float).to(self.actor.device)
        mu = self.actor.forward(state).to(self.actor.device)
        # print('check this variable for convergence!!! : ', mu)
        mu_prime = mu + T.tensor(np.random.normal(scale=self.noise, size=self.number_actions),
                                 dtype=T.float).to(self.actor.device)
        self.actor.train()

        return mu_prime.cpu().detach().numpy()[0]

    def save_models(self):
        self.actor.save_checkpoint()
        self.target_actor.save_checkpoint()
        self.critic_task1.save_checkpoint()
        self.critic_task2.save_checkpoint()
        self.critic_cost.save_checkpoint()
        self.target_critic_task1.save_checkpoint()
        self.target_critic_task2.save_checkpoint()
        self.target_critic_cost.save_checkpoint()

    def load_models(self):
        self.actor.load_checkpoint()
        self.target_actor.load_checkpoint()
        self.critic_task1.load_checkpoint()
        self.critic_task2.load_checkpoint()
        self.critic_cost.load_checkpoint()
        self.target_critic_task1.load_checkpoint()
        self.target_critic_task2.load_checkpoint()
        self.target_critic_cost.load_checkpoint()

    def local_learn(self, global_loss, state, action, reward_t1, reward_t2, reward_cost, state_, terminal):

        states = state
        states_ = state_
        actions = action
        rewards_t1 = reward_t1
        rewards_t2 = reward_t2
        rewards_cost = reward_cost          # [RQ1-CMDP] per-platoon violation indicator
        done = terminal
        self.global_loss = global_loss

        self.target_actor.eval()
        self.target_critic_task1.eval()
        self.target_critic_task2.eval()
        self.target_critic_cost.eval()
        self.critic_task1.eval()
        self.critic_task2.eval()
        self.critic_cost.eval()

        target_actions = self.target_actor.forward(states_).clone().detach()
        critic_value_task1_ = self.target_critic_task1.forward(states_, target_actions)
        critic_value_task1 = self.critic_task1.forward(states, actions)

        critic_value_task1_[done] = 0.0
        critic_value_task1_ = critic_value_task1_.view(-1)

        target_task1 = rewards_t1 + self.gamma*critic_value_task1_
        target_task1 = target_task1.view(self.batch_size, 1)
        self.critic_task1.train()
        self.critic_task1.optimizer.zero_grad()
        critic_loss_task1 = F.mse_loss(target_task1, critic_value_task1)
        critic_loss_task1.backward()
        self.critic_task1.optimizer.step()
        self.critic_task1.eval()

        critic_value_task2_ = self.target_critic_task2.forward(states_, target_actions)
        critic_value_task2 = self.critic_task2.forward(states, actions)

        critic_value_task2_[done] = 0.0
        critic_value_task2_ = critic_value_task2_.view(-1)

        # [RQ1-CMDP A1] raw/RCPO arm folds the constraint penalty into the task-2 reward target
        # (using the LIVE lambda_j); the 'critic' arm leaves task-2 untouched and instead prices the
        # constraint off the separate cost critic in the actor loss below.
        rt2 = rewards_t2
        if self.constraint_mode == 'hard' and self.cost_source == 'raw':
            rt2 = rewards_t2 - self.lam * rewards_cost
        target_task2 = rt2 + self.gamma*critic_value_task2_
        target_task2 = target_task2.view(self.batch_size, 1)

        self.critic_task2.train()
        self.critic_task2.optimizer.zero_grad()
        critic_loss_task2 = F.mse_loss(target_task2, critic_value_task2)
        critic_loss_task2.backward()
        self.critic_task2.optimizer.step()
        self.critic_task2.eval()

        # [RQ1-CMDP] cost critic: Bellman regression on the per-platoon
        # AoI-violation indicator (only used by the 'hard' actor objective).
        critic_value_cost_ = self.target_critic_cost.forward(states_, target_actions)
        critic_value_cost = self.critic_cost.forward(states, actions)
        critic_value_cost_[done] = 0.0
        critic_value_cost_ = critic_value_cost_.view(-1)
        target_cost = rewards_cost + self.gamma * critic_value_cost_
        target_cost = target_cost.view(self.batch_size, 1)
        self.critic_cost.train()
        self.critic_cost.optimizer.zero_grad()
        critic_loss_cost = F.mse_loss(target_cost, critic_value_cost)
        critic_loss_cost.backward()
        self.critic_cost.optimizer.step()
        self.critic_cost.eval()

        self.actor.optimizer.zero_grad()
        self.actor.train()
        actor_loss = -self.critic_task1.forward(states, self.actor.forward(states)) \
                     - self.critic_task2.forward(states, self.actor.forward(states))
        actor_loss = T.mean(actor_loss)
        if self.constraint_mode == 'hard':
            if self.cost_source == 'raw':
                # [RQ1-CMDP A1] RCPO-style: the penalty was folded into the task-2 target above;
                # the separate cost critic Q^c is NOT used by the actor (computed no-grad below only
                # for the cost_force / critic_loss_cost diagnostics).
                with T.no_grad():
                    qc_pi = T.mean(self.critic_cost.forward(states, self.actor.forward(states)))
            else:
                # ours: CMDP primal step minimises reward-loss + lambda_j * E[discounted cost],
                # priced off the LEARNED cost critic Q^c. The global-critic term is dropped here
                # (it is detached/zero-gradient under the original code anyway).
                qc_pi = T.mean(self.critic_cost.forward(states, self.actor.forward(states)))
                actor_loss = actor_loss + self.lam * qc_pi
        else:
            # original 'soft' behaviour (AoI enters as a reward penalty in task2);
            # the global-critic term is the original detached, zero-gradient add.
            actor_loss = actor_loss + (T.mean(self.global_loss) * 2)
            with T.no_grad():   # [RQ1-CMDP] diagnostics only (no graph, no RNG)
                qc_pi = T.mean(self.critic_cost.forward(states, self.actor.forward(states)))
        actor_loss.backward()
        self.actor.optimizer.step()

        # [RQ1-CMDP] pure logging: per-learn-step diagnostics, aggregated per episode
        # by Main.py into critic_loss_cost.mat / cost_force.mat.
        self.diag_closs_sum += float(critic_loss_cost.detach().cpu())
        self.diag_force_sum += self.lam * float(qc_pi.detach().cpu())
        self.diag_n += 1

        self.update_network_parameters()

    def update_network_parameters(self, tau=None):
        if tau is None:
            tau = self.tau

        actor_params = self.actor.named_parameters()
        critic_params_task1 = self.critic_task1.named_parameters()
        critic_params_task2 = self.critic_task2.named_parameters()
        critic_params_cost = self.critic_cost.named_parameters()
        target_actor_params = self.target_actor.named_parameters()
        target_critic_params_task1 = self.target_critic_task1.named_parameters()
        target_critic_params_task2 = self.target_critic_task2.named_parameters()
        target_critic_params_cost = self.target_critic_cost.named_parameters()

        critic_state_dict_task1 = dict(critic_params_task1)
        critic_state_dict_task2 = dict(critic_params_task2)
        critic_state_dict_cost = dict(critic_params_cost)
        actor_state_dict = dict(actor_params)
        target_critic_state_dict_task1 = dict(target_critic_params_task1)
        target_critic_state_dict_task2 = dict(target_critic_params_task2)
        target_critic_state_dict_cost = dict(target_critic_params_cost)
        target_actor_state_dict = dict(target_actor_params)

        for name in critic_state_dict_task2:
            critic_state_dict_task2[name] = tau*critic_state_dict_task2[name].clone() + \
                                (1-tau)*target_critic_state_dict_task2[name].clone()

        for name in critic_state_dict_task1:
            critic_state_dict_task1[name] = tau*critic_state_dict_task1[name].clone() + \
                                (1-tau)*target_critic_state_dict_task1[name].clone()

        for name in critic_state_dict_cost:                       # [RQ1-CMDP]
            critic_state_dict_cost[name] = tau*critic_state_dict_cost[name].clone() + \
                                (1-tau)*target_critic_state_dict_cost[name].clone()

        for name in actor_state_dict:
             actor_state_dict[name] = tau*actor_state_dict[name].clone() + \
                                 (1-tau)*target_actor_state_dict[name].clone()

        self.target_critic_task1.load_state_dict(critic_state_dict_task1)
        self.target_critic_task2.load_state_dict(critic_state_dict_task2)
        self.target_critic_cost.load_state_dict(critic_state_dict_cost)   # [RQ1-CMDP]
        self.target_actor.load_state_dict(actor_state_dict)