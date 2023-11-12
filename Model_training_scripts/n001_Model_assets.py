# -*- coding: utf-8 -*-
"""
Models
Created on Tue May 23 15:02:16 2023

Authors: Christian Vedel, [christian-vs@sam.sdu.dk],

Purpose: Defines model classes
"""

# Set path to file path
import os
script_directory = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_directory)

# %% Libraries
import numpy as np
import pandas as pd
from transformers import BertModel, BertTokenizer, XLMRobertaTokenizer, XLMRobertaModel
import torch
import torch.nn as nn

# %% BERT finetune based on model_domain
def modelPath(model_domain):
    if(model_domain == "DK_CENSUS"):
        MDL = 'Maltehb/danish-bert-botxo' # https://huggingface.co/Maltehb/danish-bert-botxo
    elif(model_domain == "EN_MARR_CERT"):
        MDL = "bert-base-uncased" 
    elif(model_domain == "HSN_DATABASE"):
        MDL = "GroNLP/bert-base-dutch-cased"
    elif(model_domain == "Multilingual"):
        MDL = 'xlm-roberta-base'
    else:
        raise Exception("This is not implemented yet")
        
    return MDL

#%% Tokenizer
def load_tokenizer(model_domain):
    # breakpoint()
    MDL = modelPath(model_domain)
    if MDL == "xlm-roberta-base":
        tokenizer = XLMRobertaTokenizer.from_pretrained(MDL)
    else: 
        tokenizer = BertTokenizer.from_pretrained(MDL)
    return(tokenizer)

# load_tokenizer(model_domain="Multilingual")

#%% Update tokenizer
def update_tokenizer(tokenizer, df):
    # Add unseen words
    all_text = ' '.join(df.occ1.tolist())
    words_list = all_text.split()
    unique_words = set(words_list)
    all_lang_words = set(df.lang)
    unique_words.update(all_lang_words)
    unique_words.update("unk") # Unknown language token
    # Add tokens for missing words
    tokenizer.add_tokens(list(unique_words))
    
    return tokenizer

# %%
def getModel(model_domain, tokenizer):
    MDL = modelPath(model_domain)
    # Load the basic BERT model 
    if model_domain == "Multilingual":
        model = XLMRobertaModel.from_pretrained(MDL)
    else:
        model = BertModel.from_pretrained(MDL)
    
    # Adapt model size to the tokens added:
    model.resize_token_embeddings(len(tokenizer))
    
    return model

# %%
# Build the Sentiment Classifier class 
class BERTOccupationClassifier(nn.Module):
    
    # Constructor class 
    def __init__(self, n_classes, model_domain, tokenizer, dropout_rate):
        super(BERTOccupationClassifier, self).__init__()
        self.basemodel = getModel(model_domain, tokenizer)
        self.drop = nn.Dropout(p=dropout_rate)
        self.out = nn.Linear(self.basemodel.config.hidden_size, n_classes)
    
    # Forward propagaion class
    def forward(self, input_ids, attention_mask):
        outputs = self.basemodel(
          input_ids=input_ids,
          attention_mask=attention_mask
        )
        pooled_output = outputs.pooler_output
        
        #  Add a dropout layer 
        output = self.drop(pooled_output)
        return self.out(output)
    
# %%
# Build the Sentiment Classifier class 
class XMLRoBERTaOccupationClassifier(nn.Module):
    
    # Constructor class 
    def __init__(self, n_classes, model_domain, tokenizer, dropout_rate):
        super(XMLRoBERTaOccupationClassifier, self).__init__()
        self.basemodel = getModel(model_domain, tokenizer)
        self.drop = nn.Dropout(p=dropout_rate)
        self.out = nn.Linear(self.basemodel.config.hidden_size, n_classes)
    
    # Forward propagaion class
    def forward(self, input_ids, attention_mask):
        outputs = self.basemodel(
          input_ids=input_ids,
          attention_mask=attention_mask
        )
        pooled_output = outputs.pooler_output
        
        #  Add a dropout layer 
        output = self.drop(pooled_output)
        return self.out(output)
    
class CharLSTMOccupationClassifier(nn.Module):
    def __init__(self, n_outputs, input_size, hidden_size, num_layers, dropout_rate):
        super(CharLSTMOccupationClassifier, self).__init__()
        
        self.embedding = nn.Embedding(input_size, hidden_size)
        self.dropout = nn.Dropout(dropout_rate)
        self.lstm = nn.LSTM(input_size=hidden_size, hidden_size=hidden_size, 
                            num_layers=num_layers, bidirectional=True, batch_first=True)
        self.global_avg_pooling = nn.AdaptiveAvgPool1d(1)  # Global average pooling
        self.fc1 = nn.Linear(hidden_size * 2, hidden_size * 2)
        self.fc2 = nn.Linear(hidden_size * 2, hidden_size)
        self.output_layer = nn.Linear(hidden_size, n_outputs)
        self.leaky_relu = nn.LeakyReLU(0.01)

    def forward(self, input_ids):
        embedded = self.embedding(input_ids)
        dropped = self.dropout(embedded)
        lstm_out, _ = self.lstm(dropped)
        
        # Global average pooling
        pooled_output = self.global_avg_pooling(lstm_out.permute(0, 2, 1)).squeeze(-1)
        
        fc1_out = self.leaky_relu(self.fc1(pooled_output))
        fc2_out = self.leaky_relu(self.fc2(fc1_out))
        
        output = torch.sigmoid(self.output_layer(fc2_out))
        
        return output