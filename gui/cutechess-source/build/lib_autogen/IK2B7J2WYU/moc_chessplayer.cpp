/****************************************************************************
** Meta object code from reading C++ file 'chessplayer.h'
**
** Created by: The Qt Meta Object Compiler version 69 (Qt 6.12.0)
**
** WARNING! All changes made in this file will be lost!
*****************************************************************************/

#include "../../../projects/lib/src/chessplayer.h"
#include <QtCore/qmetatype.h>

#include <QtCore/qtmochelpers.h>

#include <memory>


#include <QtCore/qxptype_traits.h>
#if !defined(Q_MOC_OUTPUT_REVISION)
#error "The header file 'chessplayer.h' doesn't include <QObject>."
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
struct qt_meta_tag_ZN11ChessPlayerE_t {};
} // unnamed namespace

template <> constexpr inline auto ChessPlayer::qt_create_metaobjectdata<qt_meta_tag_ZN11ChessPlayerE_t>()
{
    namespace QMC = QtMocConstants;
    QtMocHelpers::StringRefStorage qt_stringData {
        "ChessPlayer",
        "disconnected",
        "",
        "ready",
        "startedThinking",
        "timeLeft",
        "stoppedThinking",
        "thinking",
        "MoveEvaluation",
        "eval",
        "moveMade",
        "Chess::Move",
        "move",
        "resultClaim",
        "Chess::Result",
        "result",
        "debugMessage",
        "data",
        "nameChanged",
        "name",
        "go",
        "quit",
        "kill",
        "onCrashed",
        "onTimeout"
    };

    QtMocHelpers::UintData qt_methods {
        // Signal 'disconnected'
        QtMocHelpers::SignalData<void()>(1, 2, QMC::AccessPublic, QMetaType::Void),
        // Signal 'ready'
        QtMocHelpers::SignalData<void()>(3, 2, QMC::AccessPublic, QMetaType::Void),
        // Signal 'startedThinking'
        QtMocHelpers::SignalData<void(int)>(4, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 5 },
        }}),
        // Signal 'stoppedThinking'
        QtMocHelpers::SignalData<void()>(6, 2, QMC::AccessPublic, QMetaType::Void),
        // Signal 'thinking'
        QtMocHelpers::SignalData<void(const MoveEvaluation &)>(7, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 8, 9 },
        }}),
        // Signal 'moveMade'
        QtMocHelpers::SignalData<void(const Chess::Move &)>(10, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 11, 12 },
        }}),
        // Signal 'resultClaim'
        QtMocHelpers::SignalData<void(const Chess::Result &)>(13, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 14, 15 },
        }}),
        // Signal 'debugMessage'
        QtMocHelpers::SignalData<void(const QString &)>(16, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::QString, 17 },
        }}),
        // Signal 'nameChanged'
        QtMocHelpers::SignalData<void(const QString &)>(18, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::QString, 19 },
        }}),
        // Slot 'go'
        QtMocHelpers::SlotData<void()>(20, 2, QMC::AccessPublic, QMetaType::Void),
        // Slot 'quit'
        QtMocHelpers::SlotData<void()>(21, 2, QMC::AccessPublic, QMetaType::Void),
        // Slot 'kill'
        QtMocHelpers::SlotData<void()>(22, 2, QMC::AccessPublic, QMetaType::Void),
        // Slot 'onCrashed'
        QtMocHelpers::SlotData<void()>(23, 2, QMC::AccessProtected, QMetaType::Void),
        // Slot 'onTimeout'
        QtMocHelpers::SlotData<void()>(24, 2, QMC::AccessProtected, QMetaType::Void),
    };
    QtMocHelpers::UintData qt_properties {
    };
    QtMocHelpers::UintData qt_enums {
    };
    return QtMocHelpers::metaObjectData<ChessPlayer, qt_meta_tag_ZN11ChessPlayerE_t>(QMC::MetaObjectFlag{}, qt_stringData,
            qt_methods, qt_properties, qt_enums);
}
Q_CONSTINIT const QMetaObject ChessPlayer::staticMetaObject = { {
    QMetaObject::SuperData::link<QObject::staticMetaObject>(),
    qt_staticMetaObjectStaticContent<qt_meta_tag_ZN11ChessPlayerE_t>.stringdata,
    qt_staticMetaObjectStaticContent<qt_meta_tag_ZN11ChessPlayerE_t>.data,
    qt_static_metacall,
    nullptr,
    qt_staticMetaObjectRelocatingContent<qt_meta_tag_ZN11ChessPlayerE_t>.metaTypes,
    nullptr
} };

void ChessPlayer::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    auto *_t = static_cast<ChessPlayer *>(_o);
    if (_c == QMetaObject::InvokeMetaMethod) {
        switch (_id) {
        case 0: _t->disconnected(); break;
        case 1: _t->ready(); break;
        case 2: _t->startedThinking((*reinterpret_cast<std::add_pointer_t<int>>(_a[1]))); break;
        case 3: _t->stoppedThinking(); break;
        case 4: _t->thinking((*reinterpret_cast<std::add_pointer_t<MoveEvaluation>>(_a[1]))); break;
        case 5: _t->moveMade((*reinterpret_cast<std::add_pointer_t<Chess::Move>>(_a[1]))); break;
        case 6: _t->resultClaim((*reinterpret_cast<std::add_pointer_t<Chess::Result>>(_a[1]))); break;
        case 7: _t->debugMessage((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1]))); break;
        case 8: _t->nameChanged((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1]))); break;
        case 9: _t->go(); break;
        case 10: _t->quit(); break;
        case 11: _t->kill(); break;
        case 12: _t->onCrashed(); break;
        case 13: _t->onTimeout(); break;
        default: ;
        }
    }
    if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        switch (_id) {
        default: *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType(); break;
        case 4:
            switch (*reinterpret_cast<int*>(_a[1])) {
            default: *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType(); break;
            case 0:
                *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType::fromType< MoveEvaluation >(); break;
            }
            break;
        case 5:
            switch (*reinterpret_cast<int*>(_a[1])) {
            default: *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType(); break;
            case 0:
                *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType::fromType< Chess::Move >(); break;
            }
            break;
        case 6:
            switch (*reinterpret_cast<int*>(_a[1])) {
            default: *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType(); break;
            case 0:
                *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType::fromType< Chess::Result >(); break;
            }
            break;
        }
    }
    if (_c == QMetaObject::IndexOfMethod) {
        if (QtMocHelpers::indexOfMethod<void (ChessPlayer::*)()>(_a, &ChessPlayer::disconnected, 0))
            return;
        if (QtMocHelpers::indexOfMethod<void (ChessPlayer::*)()>(_a, &ChessPlayer::ready, 1))
            return;
        if (QtMocHelpers::indexOfMethod<void (ChessPlayer::*)(int )>(_a, &ChessPlayer::startedThinking, 2))
            return;
        if (QtMocHelpers::indexOfMethod<void (ChessPlayer::*)()>(_a, &ChessPlayer::stoppedThinking, 3))
            return;
        if (QtMocHelpers::indexOfMethod<void (ChessPlayer::*)(const MoveEvaluation & )>(_a, &ChessPlayer::thinking, 4))
            return;
        if (QtMocHelpers::indexOfMethod<void (ChessPlayer::*)(const Chess::Move & )>(_a, &ChessPlayer::moveMade, 5))
            return;
        if (QtMocHelpers::indexOfMethod<void (ChessPlayer::*)(const Chess::Result & )>(_a, &ChessPlayer::resultClaim, 6))
            return;
        if (QtMocHelpers::indexOfMethod<void (ChessPlayer::*)(const QString & )>(_a, &ChessPlayer::debugMessage, 7))
            return;
        if (QtMocHelpers::indexOfMethod<void (ChessPlayer::*)(const QString & )>(_a, &ChessPlayer::nameChanged, 8))
            return;
    }
}

const QMetaObject *ChessPlayer::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *ChessPlayer::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_staticMetaObjectStaticContent<qt_meta_tag_ZN11ChessPlayerE_t>.strings))
        return static_cast<void*>(this);
    return QObject::qt_metacast(_clname);
}

int ChessPlayer::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = QObject::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 14)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 14;
    }
    if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 14)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 14;
    }
    return _id;
}

// SIGNAL 0
void ChessPlayer::disconnected()
{
    QMetaObject::activate(this, &staticMetaObject, 0, nullptr);
}

// SIGNAL 1
void ChessPlayer::ready()
{
    QMetaObject::activate(this, &staticMetaObject, 1, nullptr);
}

// SIGNAL 2
void ChessPlayer::startedThinking(int _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 2, nullptr, _t1);
}

// SIGNAL 3
void ChessPlayer::stoppedThinking()
{
    QMetaObject::activate(this, &staticMetaObject, 3, nullptr);
}

// SIGNAL 4
void ChessPlayer::thinking(const MoveEvaluation & _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 4, nullptr, _t1);
}

// SIGNAL 5
void ChessPlayer::moveMade(const Chess::Move & _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 5, nullptr, _t1);
}

// SIGNAL 6
void ChessPlayer::resultClaim(const Chess::Result & _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 6, nullptr, _t1);
}

// SIGNAL 7
void ChessPlayer::debugMessage(const QString & _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 7, nullptr, _t1);
}

// SIGNAL 8
void ChessPlayer::nameChanged(const QString & _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 8, nullptr, _t1);
}
QT_WARNING_POP
