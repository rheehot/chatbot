# char train and char predict
# it work successfully but it is too sensitive
# so i don't use it anymore


from __future__ import print_function
from keras.models import Model
from keras.layers import Input, LSTM, Dense
import numpy as np

batch_size = 16  # Batch size for training.
epochs = 1  # Number of epochs to train for.
latent_dim = 512  # Latent dimensionality of the encoding space.
num_samples = 10000  # Number of samples to train on.
# Path to the data txt file on disk.
data_path = 'mydata.txt'

# Vectorize the data.
input_texts = []
target_texts = []
input_characters = set()
target_characters = set()
with open(data_path, 'r', encoding='utf-8') as f:
    lines = f.read().split('\n')
for line in lines[: min(num_samples, len(lines) - 1)]:
    input_text, target_text = line.split('\t')
    # We use "tab" as the "start sequence" character
    # for the targets, and "\n" as "end sequence" character.
    target_text = '\t ' + target_text + ' \n'
    input_texts.append(input_text)
    target_texts.append(target_text)
    #print(input_texts, target_texts,12345)
    for char in input_text:
        if char not in input_characters:
            input_characters.add(char)
    for char in target_text:
        if char not in target_characters:
            target_characters.add(char)
    #print(input_characters, target_characters,54321)

input_characters = sorted(list(input_characters))
target_characters = sorted(list(target_characters))
num_encoder_tokens = len(input_characters)
num_decoder_tokens = len(target_characters)
max_encoder_seq_length = max([len(txt) for txt in input_texts])
max_decoder_seq_length = max([len(txt) for txt in target_texts])

print('데이터 문장 개수:', len(input_texts))
print('고유한 인풋데이터   토큰 개수:', num_encoder_tokens)
print('고유한 아웃풋데이터 토큰 개수:', num_decoder_tokens)
print('가장 긴 인풋데이터   시퀀스 길이:', max_encoder_seq_length)
print('가장 긴 아웃풋데이터 시퀀스 길이:', max_decoder_seq_length)

input_token_index = dict(
    [(char, i) for i, char in enumerate(input_characters)])
target_token_index = dict(
    [(char, i) for i, char in enumerate(target_characters)])

print(input_token_index)
print(target_token_index)

encoder_input_data = np.zeros(
    (len(input_texts), max_encoder_seq_length, num_encoder_tokens),
    dtype='float32')
decoder_input_data = np.zeros(
    (len(input_texts), max_decoder_seq_length, num_decoder_tokens),
    dtype='float32')
decoder_target_data = np.zeros(
    (len(input_texts), max_decoder_seq_length, num_decoder_tokens),
    dtype='float32')


print("인코더 인풋의 shape:", encoder_input_data.shape)
print("디코더 인풋의 shape:", decoder_input_data.shape)
print("디코더 타겟의 shape:", decoder_target_data.shape)


for i, (input_text, target_text) in enumerate(zip(input_texts, target_texts)):
    for t, char in enumerate(input_text):
        encoder_input_data[i, t, input_token_index[char]] = 1.
    for t, char in enumerate(target_text):
        # decoder_target_data is ahead of decoder_input_data by one timestep
        decoder_input_data[i, t, target_token_index[char]] = 1.
        if t > 0:
            # decoder_target_data will be ahead by one timestep
            # and will not include the start character.
            decoder_target_data[i, t - 1, target_token_index[char]] = 1.
    #print(encoder_input_data[0],10000)

# Define an input sequence and process it.
encoder_inputs = Input(shape=(None, num_encoder_tokens))
print("인코더 인풋:", encoder_inputs)
encoder = LSTM(latent_dim, return_state=True)
print("인코더:", encoder)
encoder_outputs, state_h, state_c = encoder(encoder_inputs)
print("인코더 아웃풋:", encoder_outputs)
# We discard `encoder_outputs` and only keep the states.
encoder_states = [state_h, state_c]
print("인코더 상태:", encoder_states)
print()
# Set up the decoder, using `encoder_states` as initial state.
decoder_inputs = Input(shape=(None, num_decoder_tokens))
print("디코더 인풋:", decoder_inputs)
# We set up our decoder to return full output sequences,
# and to return internal states as well. We don't use the
# return states in the training model, but we will use them in inference.
decoder_lstm = LSTM(latent_dim, return_sequences=True, return_state=True)
print("decoder_lstm:", decoder_lstm)
decoder_outputs, _, _ = decoder_lstm(decoder_inputs,
                                     initial_state=encoder_states)
print("decoder_outputs:", decoder_outputs)
decoder_dense = Dense(num_decoder_tokens, activation='softmax')
print("decoder_dense:", decoder_dense)
decoder_outputs = decoder_dense(decoder_outputs)
print("decoder_outputs:", decoder_outputs)
# Define the model that will turn
# `encoder_input_data` & `decoder_input_data` into `decoder_target_data`
model = Model([encoder_inputs, decoder_inputs], decoder_outputs)

# Run training
model.compile(optimizer='rmsprop', loss='categorical_crossentropy')
model.fit([encoder_input_data, decoder_input_data], decoder_target_data,
          batch_size=batch_size,
          epochs=epochs,
          validation_split=0.2)
# Save model
model.save('s2s.h5')

# todo:Next: inference mode (sampling).
# Here's the drill:
# 1) encode input and retrieve initial decoder state
# 2) run one step of decoder with this initial state
# and a "start of sequence" token as target.
# Output will be the next target token
# 3) Repeat with the current target token and current states

print()
# Define sampling models
encoder_model = Model(encoder_inputs, encoder_states)
print("encoder_model:", encoder_model)
decoder_state_input_h = Input(shape=(latent_dim,))
print("decoder_state_input_h", decoder_state_input_h)
decoder_state_input_c = Input(shape=(latent_dim,))
print("decoder_state_input_c", decoder_state_input_c)
decoder_states_inputs = [decoder_state_input_h, decoder_state_input_c]
print("decoder_states_inputs:", decoder_states_inputs)
decoder_outputs, state_h, state_c = decoder_lstm(
    decoder_inputs, initial_state=decoder_states_inputs)
print("decoder_outputs:", decoder_outputs)
decoder_states = [state_h, state_c]
print("decoder_states:", decoder_states)
decoder_outputs = decoder_dense(decoder_outputs)
print("decoder_outputs:", decoder_outputs)
decoder_model = Model(
    [decoder_inputs] + decoder_states_inputs,
    [decoder_outputs] + decoder_states)
print("decoder_model:", decoder_model)
# Reverse-lookup token index to decode sequences back to
# something readable.
reverse_input_char_index = dict(
    (i, char) for char, i in input_token_index.items())
reverse_target_char_index = dict(
    (i, char) for char, i in target_token_index.items())


def decode_sequence(input_seq):
    # Encode the input as state vectors.
    states_value = encoder_model.predict(input_seq)

    # Generate empty target sequence of length 1.
    target_seq = np.zeros((1, 1, num_decoder_tokens))
    # Populate the first character of target sequence with the start character.
    target_seq[0, 0, target_token_index['\t']] = 1.
    # Sampling loop for a batch of sequences
    # (to simplify, here we assume a batch of size 1).
    stop_condition = False
    decoded_sentence = ''
    while not stop_condition:
        output_tokens, h, c = decoder_model.predict(
            [target_seq] + states_value)

        # Sample a token
        sampled_token_index = np.argmax(output_tokens[0, -1, :])
        sampled_char = reverse_target_char_index[sampled_token_index]
        decoded_sentence += sampled_char

        # Exit condition: either hit max length
        # or find stop character.
        if (sampled_char == '\n' or
           len(decoded_sentence) > max_decoder_seq_length):
            stop_condition = True

        # Update the target sequence (of length 1).
        target_seq = np.zeros((1, 1, num_decoder_tokens))
        target_seq[0, 0, sampled_token_index] = 1.

        # Update states
        states_value = [h, c]

    return decoded_sentence


for seq_index in range(100):
    # Take one sequence (part of the training set)
    # for trying out decoding.
    input_seq = encoder_input_data[seq_index: seq_index + 1]
    decoded_sentence = decode_sequence(input_seq)
    print('-')
    print('Input sentence:', input_texts[seq_index])
    print('Decoded sentence:', decoded_sentence)