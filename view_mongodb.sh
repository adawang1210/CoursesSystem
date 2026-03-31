#!/bin/bash

# MongoDB 數據庫查看腳本
# 用於快速查看 courses_system 數據庫的內容

echo "================================================"
echo "MongoDB 數據庫內容查看工具"
echo "================================================"
echo ""
echo "數據庫: courses_system"
echo "連接: mongodb://localhost:27017"
echo ""
echo "================================================"
echo ""

# 使用 mongosh 連接並查看所有集合
mongosh mongodb://localhost:27017/courses_system --eval "
    print('所有集合 (Collections):');
    print('----------------------------------------');
    db.getCollectionNames().forEach(function(collection) {
        var count = db[collection].countDocuments();
        print('  [v] ' + collection + ' (' + count + ' 筆資料)');
    });
    print('');
    print('================================================');
    print('各集合詳細資料:');
    print('================================================');
    print('');
    
    // 顯示課程資料
    print('課程 (courses):');
    print('----------------------------------------');
    db.courses.find().limit(5).forEach(function(doc) {
        printjson(doc);
        print('');
    });
    
    // 顯示問題資料
    print('問題 (questions):');
    print('----------------------------------------');
    db.questions.find().limit(5).forEach(function(doc) {
        printjson(doc);
        print('');
    });
    
    // 顯示問答資料
    print('問答 (qas):');
    print('----------------------------------------');
    db.qas.find().limit(5).forEach(function(doc) {
        printjson(doc);
        print('');
    });
    
    // 顯示公告資料
    print('公告 (announcements):');
    print('----------------------------------------');
    db.announcements.find().limit(5).forEach(function(doc) {
        printjson(doc);
        print('');
    });
    
    print('================================================');
    print('查詢完成！');
    print('如需查看特定集合，使用:');
    print('  mongosh mongodb://localhost:27017/courses_system');
    print('  然後執行: db.集合名稱.find().pretty()');
    print('================================================');
"

