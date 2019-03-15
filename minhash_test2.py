#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Bước 1: chuyển file dữ liệu đầu vào thành các tập shingle
# - Shingle được hiểu là nhóm 3 từ kế nhau trong document
# - Shingle được map thành các shingle ID bằng hash CRC32
# Bước 2: Tính Minhash signatures cho mỗi document
# - Random hàm hash h(x) = (ax + b) %c
# + các hệ số a, b là số ngẫu nhiên, nhỏ hơn max của x
# + x là số nguyên input đầu vào, max là 2^32 -1
# + c là số nguyên tố lớn hơn max của x (lớn hơn gần nhất)
# - Random hàm hash 10 lần, ta sẽ có list signature cho document
# Bước 3: So sánh các document qua MinHash signature
# - Giá trị tương tự giữa 2 document = số lượng signature bằng nhau / tổng số signature duy nhất trong cả 2 document
# - In ra cặp document và signature tương ứng mà có giá trị tương tự lớn hơn số threshold cho trước
# - Thresohold là giá trị định trước, xác định giá trị tương tự chấp nhận được giữa 2 document

from __future__ import division
import random
import time
import binascii
import sys

# số lần hash
num_hash = 10

# size của tập data
num_doc = 2500

data_file = "./data/articles_" + str(num_doc) + ".train"
truth_file = "./data/articles_" + str(num_doc) + ".truth"

# dictionary lưu lại cặp document giống nhau
plagiaries = {}

# dictionary lưu lại signature của các document
docs_as_shingle_sets = {}

# mở file data
f = open(data_file, "r")

doc_name = []

t0 = time.time()

# tổng số shingle của tất cả document
total_shingle = 0

#  tách document thành các word
for i in range(0, num_doc):
    # tách ra các word bằng cách split các dấu cách
    words = f.readline().split(" ")
    # document ID là từ đầu tiên
    doc_id = words[0]
    # lưu lại vào doc_name
    doc_name.append(doc_id)

    del words[0]

    # lưu lại tất cả shingle không trùng lặp của document hiện đang xét
    shingles_in_doc = set()

    # hash shingle của cả document
    for index in range(0, (len(words) - 2)):
        # tạo các shingle bằng cách nhóm 3 từ liền nhau
        shingle = words[index] + " " + words[index + 1] + " " + words[index + 2]
        # hash shingle theo CRC32
        crc = binascii.crc32(shingle) & 0xffffffff
        # thêm shingle hash vào shingles_in_doc, mỗi giá trị hash là duy nhất
        shingles_in_doc.add(crc)

    # lưu lại set shingle của document vào dictionary chung theo doc_id
    docs_as_shingle_sets[doc_id] = shingles_in_doc
    total_shingle = total_shingle + (len(words) - 2)

f.close()

print '\nShingling ' + str(num_doc) + ' docs took %.2f sec.' % (time.time() - t0)

# Tạo ma trận tam giác lưu giá trị tương tự của mỗi cặp document
# Số phần tử cần trong ma trận tam giác
num_element = int(num_doc * (num_doc - 1) / 2)

# Tạo mảng lưu lại giá trị tương tự
MHsig = [0 for i in range(num_element)]


# Định nghĩa hàm để map tọa độ ma trận 2 chiều  thành chỉ số ma trận 1 chiều
def get_triangle_index(i, j):
    # nếu i =j thi loai
    if i == j:
        sys.stderr.write("Can't access triangle matrix with i == j")
        sys.exit(1)
    # nếu j < i thì đổi chỗ 2 giá trị
    if j < i:
        temp = i
        i = j
        j = temp
    # index cần tìm
    k = int(i * (num_doc - (i + 1) / 2.0) + j - i) - 1

    return k


# Tạo MinHash signature
t0 = time.time()
print '\nGenerating random hash functions...'

# Max shingle ID
max_shingle_id = 2 ** 32 - 1

# giá trị c là số nguyên tố lớn gần nhất max_shingle_id
next_prime = 4294967311


# hàm hash signature của min hash: h(x) = (ax + b) % c
# chọn ngẫu nhiên cặp hệ số a,b

def pick_random_coeffs(k):
    rand_list = []

    while k > 0:
        # get random shingle ID
        rand_index = random.randint(0, max_shingle_id)

        # kiểm tra để shingle ID này là duy nhất trong rand_list
        while rand_index in rand_list:
            rand_index = random.randint(0, max_shingle_id)

        rand_list.append(rand_index)
        k = k - 1

    return rand_list


# Lấy các giá trị a, b
coeff_a = pick_random_coeffs(num_hash)
coeff_b = pick_random_coeffs(num_hash)

print '\nGenerating MinHash signatures for all documents...'

# Mảng signatures dạng vectore đại diện cho các document
signatures = []

for doc_id in doc_name:
    # lấy ra tập shingle của document này
    shingle_id_set = docs_as_shingle_sets[doc_id]

    # mảng signature cho document
    signature = []

    # sinh mảng 10 phần tử signature từ hàm hash cho mỗi document
    for i in range(0, num_hash):
        # tìm ra giá trị signature/hash code nhỏ nhất sau num_hash lần chay
        min_hash_code = next_prime + 1
        for shingle_id in shingle_id_set:
            # đầu vào hàm hash là shingle_id
            hash_code = (coeff_a[i] * shingle_id + coeff_b[i]) % next_prime

            if hash_code < min_hash_code:
                min_hash_code = hash_code

        signature.append(min_hash_code)

    signatures.append(signature)

elapsed = (time.time() - t0)
print "\nGenerating MinHash signatures took %.2fsec" % elapsed

t0 = time.time()
# So sánh các signature của document
# Tính toán phần trăm trùng signature

for i in range(0, num_doc):
    # lấy list signature cho document[i]
    signature1 = signatures[i]

    for j in range(i + 1, num_doc):
        signature2 = signatures[j]

        count = 0
        # tính số lượng signature bằng nhau
        for k in range(0, num_hash):
            count = count + (signature1[k] == signature2[k])
            if count / num_hash > 0.5:
                print("signature1[k]: " + str(signature1[k]) + ", signature2[k]: " + str(signature2[k]))

        MHsig[get_triangle_index(i, j)] = count / num_hash

elapsed = (time.time() - t0)

print "\nComparing MinHash signatures took %.2fsec" % elapsed

# In ra các cặp document tương tự
threshold = 0.5
tp = 0
fp = 0
print "                   Est. J   Act. J"
for i in range(0, num_doc):
    for j in range(i + 1, num_doc):
        est = MHsig[get_triangle_index(i, j)]

        # nếu độ tương tự của 2 document lớn hơn threhold
        if est > threshold:
            # tính độ tương tự theo phương pháp Jaccard
            s1 = docs_as_shingle_sets[doc_name[i]]
            s2 = docs_as_shingle_sets[doc_name[j]]
            J = (len(s1.intersection(s2)) / len(s1.union(s2)))
            print "  %5s --> %5s   %.2f     %.2f" % (doc_name[i], doc_name[j], est, J)
