/****************************************************************************
** Meta object code from reading C++ file 'chessgame.h'
**
** Created by: The Qt Meta Object Compiler version 69 (Qt 6.12.0)
**
** WARNING! All changes made in this file will be lost!
*****************************************************************************/

#include "../../../projects/lib/src/chessgame.h"
#include <QtCore/qmetatype.h>

#include <QtCore/qtmochelpers.h>

#include <memory>


#include <QtCore/qxptype_traits.h>
#if !defined(Q_MOC_OUTPUT_REVISION)
#error "The header file 'chessgame.h' doesn't include <QObject>."
#elif Q_MOC_OUTPUT_REVISION != 69
#error "This file was generated using the moc from 6.12.0. It"
#error "cannot be used with the include files from this version of Qt."
#error "(The moc has changed too much.)"
#endif

#ifndef Q_CONSTINIT
#define Q_CONSTINIT
#endif

QT_WARNING_PUSH
QT_WARNING_DISABLE_DEPRECATED
QT_WARNING_DISABLE_GCC("-Wuseless-cast")
namespace {
struct qt_meta_tag_ZN9ChessGameE_t {};
} // unnamed namespace

template <> constexpr inline auto ChessGame::qt_create_metaobjectdata<qt_meta_tag_ZN9ChessGameE_t>()
{
    namespace QMC = QtMocConstants;
    QtMocHelpers::StringRefStorage qt_stringData {
        "ChessGame",
        "humanEnabled",
        "",
        "fenChanged",
        "fenString",
        "moveMade",
        "Chess::GenericMove",
        "move",
        "sanString",
        "comment",
        "moveChanged",
        "ply",
        "scoreChanged",
        "score",
        "initialized",
        "ChessGame*",
        "game",
        "started",
        "finished",
        "Chess::Result",
        "result",
        "startFailed",
        "playersReady",
        "start",
        "pause",
        "resume",
        "stop",
        "emitMoveChanged",
        "kill",
        "emitStartFailed",
        "onMoveMade",
        "Chess::Move",
        "onAdjudication",
        "onResignation",
        "startGame",
        "startTurn",
        "finish",
        "onResultClaim",
        "onPlayerReady",
        "syncPlayers",
        "pauseThread"
    };

    QtMocHelpers::UintData qt_methods {
        // Signal 'humanEnabled'
        QtMocHelpers::SignalData<void(bool)>(1, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Bool, 2 },
        }}),
        // Signal 'fenChanged'
        QtMocHelpers::SignalData<void(const QString &)>(3, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::QString, 4 },
        }}),
        // Signal 'moveMade'
        QtMocHelpers::SignalData<void(const Chess::GenericMove &, const QString &, const QString &)>(5, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 6, 7 }, { QMetaType::QString, 8 }, { QMetaType::QString, 9 },
        }}),
        // Signal 'moveChanged'
        QtMocHelpers::SignalData<void(int, const Chess::GenericMove &, const QString &, const QString &)>(10, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 11 }, { 0x80000000 | 6, 7 }, { QMetaType::QString, 8 }, { QMetaType::QString, 9 },
        }}),
        // Signal 'scoreChanged'
        QtMocHelpers::SignalData<void(int, int)>(12, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 11 }, { QMetaType::Int, 13 },
        }}),
        // Signal 'initialized'
        QtMocHelpers::SignalData<void(ChessGame *)>(14, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 15, 16 },
        }}),
        // Signal 'initialized'
        QtMocHelpers::SignalData<void()>(14, 2, QMC::AccessPublic | QMC::MethodCloned, QMetaType::Void),
        // Signal 'started'
        QtMocHelpers::SignalData<void(ChessGame *)>(17, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 15, 16 },
        }}),
        // Signal 'started'
        QtMocHelpers::SignalData<void()>(17, 2, QMC::AccessPublic | QMC::MethodCloned, QMetaType::Void),
        // Signal 'finished'
        QtMocHelpers::SignalData<void(ChessGame *, Chess::Result)>(18, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 15, 16 }, { 0x80000000 | 19, 20 },
        }}),
        // Signal 'finished'
        QtMocHelpers::SignalData<void(ChessGame *)>(18, 2, QMC::AccessPublic | QMC::MethodCloned, QMetaType::Void, {{
            { 0x80000000 | 15, 16 },
        }}),
        // Signal 'finished'
        QtMocHelpers::SignalData<void()>(18, 2, QMC::AccessPublic | QMC::MethodCloned, QMetaType::Void),
        // Signal 'startFailed'
        QtMocHelpers::SignalData<void(ChessGame *)>(21, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 15, 16 },
        }}),
        // Signal 'startFailed'
        QtMocHelpers::SignalData<void()>(21, 2, QMC::AccessPublic | QMC::MethodCloned, QMetaType::Void),
        // Signal 'playersReady'
        QtMocHelpers::SignalData<void()>(22, 2, QMC::AccessPublic, QMetaType::Void),
        // Slot 'start'
        QtMocHelpers::SlotData<void()>(23, 2, QMC::AccessPublic, QMetaType::Void),
        // Slot 'pause'
        QtMocHelpers::SlotData<void()>(24, 2, QMC::AccessPublic, QMetaType::Void),
        // Slot 'resume'
        QtMocHelpers::SlotData<void()>(25, 2, QMC::AccessPublic, QMetaType::Void),
        // Slot 'stop'
        QtMocHelpers::SlotData<void(bool)>(26, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Bool, 27 },
        }}),
        // Slot 'stop'
        QtMocHelpers::SlotData<void()>(26, 2, QMC::AccessPublic | QMC::MethodCloned, QMetaType::Void),
        // Slot 'kill'
        QtMocHelpers::SlotData<void()>(28, 2, QMC::AccessPublic, QMetaType::Void),
        // Slot 'emitStartFailed'
        QtMocHelpers::SlotData<void()>(29, 2, QMC::AccessPublic, QMetaType::Void),
        // Slot 'onMoveMade'
        QtMocHelpers::SlotData<void(const Chess::Move &)>(30, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 31, 7 },
        }}),
        // Slot 'onAdjudication'
        QtMocHelpers::SlotData<void(const Chess::Result &)>(32, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 19, 20 },
        }}),
        // Slot 'onResignation'
        QtMocHelpers::SlotData<void(const Chess::Result &)>(33, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 19, 20 },
        }}),
        // Slot 'startGame'
        QtMocHelpers::SlotData<void()>(34, 2, QMC::AccessPrivate, QMetaType::Void),
        // Slot 'startTurn'
        QtMocHelpers::SlotData<void()>(35, 2, QMC::AccessPrivate, QMetaType::Void),
        // Slot 'finish'
        QtMocHelpers::SlotData<void()>(36, 2, QMC::AccessPrivate, QMetaType::Void),
        // Slot 'onResultClaim'
        QtMocHelpers::SlotData<void(const Chess::Result &)>(37, 2, QMC::AccessPrivate, QMetaType::Void, {{
            { 0x80000000 | 19, 20 },
        }}),
        // Slot 'onPlayerReady'
        QtMocHelpers::SlotData<void()>(38, 2, QMC::AccessPrivate, QMetaType::Void),
        // Slot 'syncPlayers'
        QtMocHelpers::SlotData<void()>(39, 2, QMC::AccessPrivate, QMetaType::Void),
        // Slot 'pauseThread'
        QtMocHelpers::SlotData<void()>(40, 2, QMC::AccessPrivate, QMetaType::Void),
    };
    QtMocHelpers::UintData qt_properties {
    };
    QtMocHelpers::UintData qt_enums {
    };
    return QtMocHelpers::metaObjectData<ChessGame, qt_meta_tag_ZN9ChessGameE_t>(QMC::MetaObjectFlag{}, qt_stringData,
            qt_methods, qt_properties, qt_enums);
}
Q_CONSTINIT const QMetaObject ChessGame::staticMetaObject = { {
    QMetaObject::SuperData::link<QObject::staticMetaObject>(),
    qt_staticMetaObjectStaticContent<qt_meta_tag_ZN9ChessGameE_t>.stringdata,
    qt_staticMetaObjectStaticContent<qt_meta_tag_ZN9ChessGameE_t>.data,
    qt_static_metacall,
    nullptr,
    qt_staticMetaObjectRelocatingContent<qt_meta_tag_ZN9ChessGameE_t>.metaTypes,
    nullptr
} };

void ChessGame::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    auto *_t = static_cast<ChessGame *>(_o);
    if (_c == QMetaObject::InvokeMetaMethod) {
        switch (_id) {
        case 0: _t->humanEnabled((*reinterpret_cast<std::add_pointer_t<bool>>(_a[1]))); break;
        case 1: _t->fenChanged((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1]))); break;
        case 2: _t->moveMade((*reinterpret_cast<std::add_pointer_t<Chess::GenericMove>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[2])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[3]))); break;
        case 3: _t->moveChanged((*reinterpret_cast<std::add_pointer_t<int>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<Chess::GenericMove>>(_a[2])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[3])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[4]))); break;
        case 4: _t->scoreChanged((*reinterpret_cast<std::add_pointer_t<int>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<int>>(_a[2]))); break;
        case 5: _t->initialized((*reinterpret_cast<std::add_pointer_t<ChessGame*>>(_a[1]))); break;
        case 6: _t->initialized(); break;
        case 7: _t->started((*reinterpret_cast<std::add_pointer_t<ChessGame*>>(_a[1]))); break;
        case 8: _t->started(); break;
        case 9: _t->finished((*reinterpret_cast<std::add_pointer_t<ChessGame*>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<Chess::Result>>(_a[2]))); break;
        case 10: _t->finished((*reinterpret_cast<std::add_pointer_t<ChessGame*>>(_a[1]))); break;
        case 11: _t->finished(); break;
        case 12: _t->startFailed((*reinterpret_cast<std::add_pointer_t<ChessGame*>>(_a[1]))); break;
        case 13: _t->startFailed(); break;
        case 14: _t->playersReady(); break;
        case 15: _t->start(); break;
        case 16: _t->pause(); break;
        case 17: _t->resume(); break;
        case 18: _t->stop((*reinterpret_cast<std::add_pointer_t<bool>>(_a[1]))); break;
        case 19: _t->stop(); break;
        case 20: _t->kill(); break;
        case 21: _t->emitStartFailed(); break;
        case 22: _t->onMoveMade((*reinterpret_cast<std::add_pointer_t<Chess::Move>>(_a[1]))); break;
        case 23: _t->onAdjudication((*reinterpret_cast<std::add_pointer_t<Chess::Result>>(_a[1]))); break;
        case 24: _t->onResignation((*reinterpret_cast<std::add_pointer_t<Chess::Result>>(_a[1]))); break;
        case 25: _t->startGame(); break;
        case 26: _t->startTurn(); break;
        case 27: _t->finish(); break;
        case 28: _t->onResultClaim((*reinterpret_cast<std::add_pointer_t<Chess::Result>>(_a[1]))); break;
        case 29: _t->onPlayerReady(); break;
        case 30: _t->syncPlayers(); break;
        case 31: _t->pauseThread(); break;
        default: ;
        }
    }
    if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        switch (_id) {
        default: *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType(); break;
        case 2:
            switch (*reinterpret_cast<int*>(_a[1])) {
            default: *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType(); break;
            case 0:
                *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType::fromType< Chess::GenericMove >(); break;
            }
            break;
        case 3:
            switch (*reinterpret_cast<int*>(_a[1])) {
            default: *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType(); break;
            case 1:
                *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType::fromType< Chess::GenericMove >(); break;
            }
            break;
        case 5:
            switch (*reinterpret_cast<int*>(_a[1])) {
            default: *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType(); break;
            case 0:
                *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType::fromType< ChessGame* >(); break;
            }
            break;
        case 7:
            switch (*reinterpret_cast<int*>(_a[1])) {
            default: *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType(); break;
            case 0:
                *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType::fromType< ChessGame* >(); break;
            }
            break;
        case 9:
            switch (*reinterpret_cast<int*>(_a[1])) {
            default: *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType(); break;
            case 1:
                *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType::fromType< Chess::Result >(); break;
            case 0:
                *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType::fromType< ChessGame* >(); break;
            }
            break;
        case 10:
            switch (*reinterpret_cast<int*>(_a[1])) {
            default: *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType(); break;
            case 0:
                *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType::fromType< ChessGame* >(); break;
            }
            break;
        case 12:
            switch (*reinterpret_cast<int*>(_a[1])) {
            default: *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType(); break;
            case 0:
                *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType::fromType< ChessGame* >(); break;
            }
            break;
        case 22:
            switch (*reinterpret_cast<int*>(_a[1])) {
            default: *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType(); break;
            case 0:
                *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType::fromType< Chess::Move >(); break;
            }
            break;
        case 23:
            switch (*reinterpret_cast<int*>(_a[1])) {
            default: *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType(); break;
            case 0:
                *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType::fromType< Chess::Result >(); break;
            }
            break;
        case 24:
            switch (*reinterpret_cast<int*>(_a[1])) {
            default: *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType(); break;
            case 0:
                *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType::fromType< Chess::Result >(); break;
            }
            break;
        case 28:
            switch (*reinterpret_cast<int*>(_a[1])) {
            default: *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType(); break;
            case 0:
                *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType::fromType< Chess::Result >(); break;
            }
            break;
        }
    }
    if (_c == QMetaObject::IndexOfMethod) {
        if (QtMocHelpers::indexOfMethod<void (ChessGame::*)(bool )>(_a, &ChessGame::humanEnabled, 0))
            return;
        if (QtMocHelpers::indexOfMethod<void (ChessGame::*)(const QString & )>(_a, &ChessGame::fenChanged, 1))
            return;
        if (QtMocHelpers::indexOfMethod<void (ChessGame::*)(const Chess::GenericMove & , const QString & , const QString & )>(_a, &ChessGame::moveMade, 2))
            return;
        if (QtMocHelpers::indexOfMethod<void (ChessGame::*)(int , const Chess::GenericMove & , const QString & , const QString & )>(_a, &ChessGame::moveChanged, 3))
            return;
        if (QtMocHelpers::indexOfMethod<void (ChessGame::*)(int , int )>(_a, &ChessGame::scoreChanged, 4))
            return;
        if (QtMocHelpers::indexOfMethod<void (ChessGame::*)(ChessGame * )>(_a, &ChessGame::initialized, 5))
            return;
        if (QtMocHelpers::indexOfMethod<void (ChessGame::*)(ChessGame * )>(_a, &ChessGame::started, 7))
            return;
        if (QtMocHelpers::indexOfMethod<void (ChessGame::*)(ChessGame * , Chess::Result )>(_a, &ChessGame::finished, 9))
            return;
        if (QtMocHelpers::indexOfMethod<void (ChessGame::*)(ChessGame * )>(_a, &ChessGame::startFailed, 12))
            return;
        if (QtMocHelpers::indexOfMethod<void (ChessGame::*)()>(_a, &ChessGame::playersReady, 14))
            return;
    }
}

const QMetaObject *ChessGame::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *ChessGame::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_staticMetaObjectStaticContent<qt_meta_tag_ZN9ChessGameE_t>.strings))
        return static_cast<void*>(this);
    return QObject::qt_metacast(_clname);
}

int ChessGame::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = QObject::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 32)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 32;
    }
    if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 32)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 32;
    }
    return _id;
}

// SIGNAL 0
void ChessGame::humanEnabled(bool _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 0, nullptr, _t1);
}

// SIGNAL 1
void ChessGame::fenChanged(const QString & _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 1, nullptr, _t1);
}

// SIGNAL 2
void ChessGame::moveMade(const Chess::GenericMove & _t1, const QString & _t2, const QString & _t3)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 2, nullptr, _t1, _t2, _t3);
}

// SIGNAL 3
void ChessGame::moveChanged(int _t1, const Chess::GenericMove & _t2, const QString & _t3, const QString & _t4)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 3, nullptr, _t1, _t2, _t3, _t4);
}

// SIGNAL 4
void ChessGame::scoreChanged(int _t1, int _t2)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 4, nullptr, _t1, _t2);
}

// SIGNAL 5
void ChessGame::initialized(ChessGame * _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 5, nullptr, _t1);
}

// SIGNAL 7
void ChessGame::started(ChessGame * _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 7, nullptr, _t1);
}

// SIGNAL 9
void ChessGame::finished(ChessGame * _t1, Chess::Result _t2)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 9, nullptr, _t1, _t2);
}

// SIGNAL 12
void ChessGame::startFailed(ChessGame * _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 12, nullptr, _t1);
}

// SIGNAL 14
void ChessGame::playersReady()
{
    QMetaObject::activate(this, &staticMetaObject, 14, nullptr);
}
QT_WARNING_POP
