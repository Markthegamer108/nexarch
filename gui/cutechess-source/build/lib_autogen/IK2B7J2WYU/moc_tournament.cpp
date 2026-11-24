/****************************************************************************
** Meta object code from reading C++ file 'tournament.h'
**
** Created by: The Qt Meta Object Compiler version 69 (Qt 6.12.0)
**
** WARNING! All changes made in this file will be lost!
*****************************************************************************/

#include "../../../projects/lib/src/tournament.h"
#include <QtCore/qmetatype.h>

#include <QtCore/qtmochelpers.h>

#include <memory>


#include <QtCore/qxptype_traits.h>
#if !defined(Q_MOC_OUTPUT_REVISION)
#error "The header file 'tournament.h' doesn't include <QObject>."
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
struct qt_meta_tag_ZN10TournamentE_t {};
} // unnamed namespace

template <> constexpr inline auto Tournament::qt_create_metaobjectdata<qt_meta_tag_ZN10TournamentE_t>()
{
    namespace QMC = QtMocConstants;
    QtMocHelpers::StringRefStorage qt_stringData {
        "Tournament",
        "gameStarted",
        "",
        "ChessGame*",
        "game",
        "number",
        "whiteIndex",
        "blackIndex",
        "gameFinished",
        "gameTerminated",
        "index",
        "Chess::Result",
        "result",
        "finished",
        "start",
        "stop",
        "startNextGame",
        "writePgn",
        "PgnGame*",
        "pgn",
        "gameNumber",
        "writeEpd",
        "onGameStarted",
        "onGameFinished",
        "onGameDestroyed",
        "onGameStartFailed"
    };

    QtMocHelpers::UintData qt_methods {
        // Signal 'gameStarted'
        QtMocHelpers::SignalData<void(ChessGame *, int, int, int)>(1, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 3, 4 }, { QMetaType::Int, 5 }, { QMetaType::Int, 6 }, { QMetaType::Int, 7 },
        }}),
        // Signal 'gameFinished'
        QtMocHelpers::SignalData<void(ChessGame *, int, int, int)>(8, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 3, 4 }, { QMetaType::Int, 5 }, { QMetaType::Int, 6 }, { QMetaType::Int, 7 },
        }}),
        // Signal 'gameTerminated'
        QtMocHelpers::SignalData<void(int, Chess::Result)>(9, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 10 }, { 0x80000000 | 11, 12 },
        }}),
        // Signal 'finished'
        QtMocHelpers::SignalData<void()>(13, 2, QMC::AccessPublic, QMetaType::Void),
        // Slot 'start'
        QtMocHelpers::SlotData<void()>(14, 2, QMC::AccessPublic, QMetaType::Void),
        // Slot 'stop'
        QtMocHelpers::SlotData<void()>(15, 2, QMC::AccessPublic, QMetaType::Void),
        // Slot 'startNextGame'
        QtMocHelpers::SlotData<void()>(16, 2, QMC::AccessPrivate, QMetaType::Void),
        // Slot 'writePgn'
        QtMocHelpers::SlotData<bool(PgnGame *, int)>(17, 2, QMC::AccessPrivate, QMetaType::Bool, {{
            { 0x80000000 | 18, 19 }, { QMetaType::Int, 20 },
        }}),
        // Slot 'writeEpd'
        QtMocHelpers::SlotData<bool(ChessGame *)>(21, 2, QMC::AccessPrivate, QMetaType::Bool, {{
            { 0x80000000 | 3, 4 },
        }}),
        // Slot 'onGameStarted'
        QtMocHelpers::SlotData<void(ChessGame *)>(22, 2, QMC::AccessPrivate, QMetaType::Void, {{
            { 0x80000000 | 3, 4 },
        }}),
        // Slot 'onGameFinished'
        QtMocHelpers::SlotData<void(ChessGame *)>(23, 2, QMC::AccessPrivate, QMetaType::Void, {{
            { 0x80000000 | 3, 4 },
        }}),
        // Slot 'onGameDestroyed'
        QtMocHelpers::SlotData<void(ChessGame *)>(24, 2, QMC::AccessPrivate, QMetaType::Void, {{
            { 0x80000000 | 3, 4 },
        }}),
        // Slot 'onGameStartFailed'
        QtMocHelpers::SlotData<void(ChessGame *)>(25, 2, QMC::AccessPrivate, QMetaType::Void, {{
            { 0x80000000 | 3, 4 },
        }}),
    };
    QtMocHelpers::UintData qt_properties {
    };
    QtMocHelpers::UintData qt_enums {
    };
    return QtMocHelpers::metaObjectData<Tournament, qt_meta_tag_ZN10TournamentE_t>(QMC::MetaObjectFlag{}, qt_stringData,
            qt_methods, qt_properties, qt_enums);
}
Q_CONSTINIT const QMetaObject Tournament::staticMetaObject = { {
    QMetaObject::SuperData::link<QObject::staticMetaObject>(),
    qt_staticMetaObjectStaticContent<qt_meta_tag_ZN10TournamentE_t>.stringdata,
    qt_staticMetaObjectStaticContent<qt_meta_tag_ZN10TournamentE_t>.data,
    qt_static_metacall,
    nullptr,
    qt_staticMetaObjectRelocatingContent<qt_meta_tag_ZN10TournamentE_t>.metaTypes,
    nullptr
} };

void Tournament::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    auto *_t = static_cast<Tournament *>(_o);
    if (_c == QMetaObject::InvokeMetaMethod) {
        switch (_id) {
        case 0: _t->gameStarted((*reinterpret_cast<std::add_pointer_t<ChessGame*>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<int>>(_a[2])),(*reinterpret_cast<std::add_pointer_t<int>>(_a[3])),(*reinterpret_cast<std::add_pointer_t<int>>(_a[4]))); break;
        case 1: _t->gameFinished((*reinterpret_cast<std::add_pointer_t<ChessGame*>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<int>>(_a[2])),(*reinterpret_cast<std::add_pointer_t<int>>(_a[3])),(*reinterpret_cast<std::add_pointer_t<int>>(_a[4]))); break;
        case 2: _t->gameTerminated((*reinterpret_cast<std::add_pointer_t<int>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<Chess::Result>>(_a[2]))); break;
        case 3: _t->finished(); break;
        case 4: _t->start(); break;
        case 5: _t->stop(); break;
        case 6: _t->startNextGame(); break;
        case 7: { bool _r = _t->writePgn((*reinterpret_cast<std::add_pointer_t<PgnGame*>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<int>>(_a[2])));
            if (_a[0]) *reinterpret_cast<bool*>(_a[0]) = std::move(_r); }  break;
        case 8: { bool _r = _t->writeEpd((*reinterpret_cast<std::add_pointer_t<ChessGame*>>(_a[1])));
            if (_a[0]) *reinterpret_cast<bool*>(_a[0]) = std::move(_r); }  break;
        case 9: _t->onGameStarted((*reinterpret_cast<std::add_pointer_t<ChessGame*>>(_a[1]))); break;
        case 10: _t->onGameFinished((*reinterpret_cast<std::add_pointer_t<ChessGame*>>(_a[1]))); break;
        case 11: _t->onGameDestroyed((*reinterpret_cast<std::add_pointer_t<ChessGame*>>(_a[1]))); break;
        case 12: _t->onGameStartFailed((*reinterpret_cast<std::add_pointer_t<ChessGame*>>(_a[1]))); break;
        default: ;
        }
    }
    if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        switch (_id) {
        default: *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType(); break;
        case 2:
            switch (*reinterpret_cast<int*>(_a[1])) {
            default: *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType(); break;
            case 1:
                *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType::fromType< Chess::Result >(); break;
            }
            break;
        }
    }
    if (_c == QMetaObject::IndexOfMethod) {
        if (QtMocHelpers::indexOfMethod<void (Tournament::*)(ChessGame * , int , int , int )>(_a, &Tournament::gameStarted, 0))
            return;
        if (QtMocHelpers::indexOfMethod<void (Tournament::*)(ChessGame * , int , int , int )>(_a, &Tournament::gameFinished, 1))
            return;
        if (QtMocHelpers::indexOfMethod<void (Tournament::*)(int , Chess::Result )>(_a, &Tournament::gameTerminated, 2))
            return;
        if (QtMocHelpers::indexOfMethod<void (Tournament::*)()>(_a, &Tournament::finished, 3))
            return;
    }
}

const QMetaObject *Tournament::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *Tournament::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_staticMetaObjectStaticContent<qt_meta_tag_ZN10TournamentE_t>.strings))
        return static_cast<void*>(this);
    return QObject::qt_metacast(_clname);
}

int Tournament::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = QObject::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 13)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 13;
    }
    if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 13)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 13;
    }
    return _id;
}

// SIGNAL 0
void Tournament::gameStarted(ChessGame * _t1, int _t2, int _t3, int _t4)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 0, nullptr, _t1, _t2, _t3, _t4);
}

// SIGNAL 1
void Tournament::gameFinished(ChessGame * _t1, int _t2, int _t3, int _t4)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 1, nullptr, _t1, _t2, _t3, _t4);
}

// SIGNAL 2
void Tournament::gameTerminated(int _t1, Chess::Result _t2)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 2, nullptr, _t1, _t2);
}

// SIGNAL 3
void Tournament::finished()
{
    QMetaObject::activate(this, &staticMetaObject, 3, nullptr);
}
namespace {
struct qt_meta_tag_ZN15ResultFormatterE_t {};
} // unnamed namespace

template <> constexpr inline auto ResultFormatter::qt_create_metaobjectdata<qt_meta_tag_ZN15ResultFormatterE_t>()
{
    namespace QMC = QtMocConstants;
    QtMocHelpers::StringRefStorage qt_stringData {
        "ResultFormatter"
    };

    QtMocHelpers::UintData qt_methods {
    };
    QtMocHelpers::UintData qt_properties {
    };
    QtMocHelpers::UintData qt_enums {
    };
    return QtMocHelpers::metaObjectData<ResultFormatter, qt_meta_tag_ZN15ResultFormatterE_t>(QMC::MetaObjectFlag{}, qt_stringData,
            qt_methods, qt_properties, qt_enums);
}
Q_CONSTINIT const QMetaObject ResultFormatter::staticMetaObject = { {
    QMetaObject::SuperData::link<QObject::staticMetaObject>(),
    qt_staticMetaObjectStaticContent<qt_meta_tag_ZN15ResultFormatterE_t>.stringdata,
    qt_staticMetaObjectStaticContent<qt_meta_tag_ZN15ResultFormatterE_t>.data,
    qt_static_metacall,
    nullptr,
    qt_staticMetaObjectRelocatingContent<qt_meta_tag_ZN15ResultFormatterE_t>.metaTypes,
    nullptr
} };

void ResultFormatter::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    auto *_t = static_cast<ResultFormatter *>(_o);
    (void)_t;
    (void)_c;
    (void)_id;
    (void)_a;
}

const QMetaObject *ResultFormatter::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *ResultFormatter::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_staticMetaObjectStaticContent<qt_meta_tag_ZN15ResultFormatterE_t>.strings))
        return static_cast<void*>(this);
    return QObject::qt_metacast(_clname);
}

int ResultFormatter::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = QObject::qt_metacall(_c, _id, _a);
    return _id;
}
QT_WARNING_POP
