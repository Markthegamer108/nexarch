/****************************************************************************
** Meta object code from reading C++ file 'chessengine.h'
**
** Created by: The Qt Meta Object Compiler version 69 (Qt 6.12.0)
**
** WARNING! All changes made in this file will be lost!
*****************************************************************************/

#include "../../../projects/lib/src/chessengine.h"
#include <QtCore/qmetatype.h>

#include <QtCore/qtmochelpers.h>

#include <memory>


#include <QtCore/qxptype_traits.h>
#if !defined(Q_MOC_OUTPUT_REVISION)
#error "The header file 'chessengine.h' doesn't include <QObject>."
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
struct qt_meta_tag_ZN11ChessEngineE_t {};
} // unnamed namespace

template <> constexpr inline auto ChessEngine::qt_create_metaobjectdata<qt_meta_tag_ZN11ChessEngineE_t>()
{
    namespace QMC = QtMocConstants;
    QtMocHelpers::StringRefStorage qt_stringData {
        "ChessEngine",
        "go",
        "",
        "quit",
        "kill",
        "onTimeout",
        "onReadyRead",
        "onPingTimeout",
        "onIdleTimeout",
        "pong",
        "emitReady",
        "onProtocolStart",
        "flushWriteBuffer",
        "clearWriteBuffer",
        "onQuitTimeout",
        "onProtocolStartTimeout"
    };

    QtMocHelpers::UintData qt_methods {
        // Slot 'go'
        QtMocHelpers::SlotData<void()>(1, 2, QMC::AccessPublic, QMetaType::Void),
        // Slot 'quit'
        QtMocHelpers::SlotData<void()>(3, 2, QMC::AccessPublic, QMetaType::Void),
        // Slot 'kill'
        QtMocHelpers::SlotData<void()>(4, 2, QMC::AccessPublic, QMetaType::Void),
        // Slot 'onTimeout'
        QtMocHelpers::SlotData<void()>(5, 2, QMC::AccessProtected, QMetaType::Void),
        // Slot 'onReadyRead'
        QtMocHelpers::SlotData<void()>(6, 2, QMC::AccessProtected, QMetaType::Void),
        // Slot 'onPingTimeout'
        QtMocHelpers::SlotData<void()>(7, 2, QMC::AccessProtected, QMetaType::Void),
        // Slot 'onIdleTimeout'
        QtMocHelpers::SlotData<void()>(8, 2, QMC::AccessProtected, QMetaType::Void),
        // Slot 'pong'
        QtMocHelpers::SlotData<void(bool)>(9, 2, QMC::AccessProtected, QMetaType::Void, {{
            { QMetaType::Bool, 10 },
        }}),
        // Slot 'pong'
        QtMocHelpers::SlotData<void()>(9, 2, QMC::AccessProtected | QMC::MethodCloned, QMetaType::Void),
        // Slot 'onProtocolStart'
        QtMocHelpers::SlotData<void()>(11, 2, QMC::AccessProtected, QMetaType::Void),
        // Slot 'flushWriteBuffer'
        QtMocHelpers::SlotData<void()>(12, 2, QMC::AccessProtected, QMetaType::Void),
        // Slot 'clearWriteBuffer'
        QtMocHelpers::SlotData<void()>(13, 2, QMC::AccessProtected, QMetaType::Void),
        // Slot 'onQuitTimeout'
        QtMocHelpers::SlotData<void()>(14, 2, QMC::AccessProtected, QMetaType::Void),
        // Slot 'onProtocolStartTimeout'
        QtMocHelpers::SlotData<void()>(15, 2, QMC::AccessProtected, QMetaType::Void),
    };
    QtMocHelpers::UintData qt_properties {
    };
    QtMocHelpers::UintData qt_enums {
    };
    return QtMocHelpers::metaObjectData<ChessEngine, qt_meta_tag_ZN11ChessEngineE_t>(QMC::MetaObjectFlag{}, qt_stringData,
            qt_methods, qt_properties, qt_enums);
}
Q_CONSTINIT const QMetaObject ChessEngine::staticMetaObject = { {
    QMetaObject::SuperData::link<ChessPlayer::staticMetaObject>(),
    qt_staticMetaObjectStaticContent<qt_meta_tag_ZN11ChessEngineE_t>.stringdata,
    qt_staticMetaObjectStaticContent<qt_meta_tag_ZN11ChessEngineE_t>.data,
    qt_static_metacall,
    nullptr,
    qt_staticMetaObjectRelocatingContent<qt_meta_tag_ZN11ChessEngineE_t>.metaTypes,
    nullptr
} };

void ChessEngine::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    auto *_t = static_cast<ChessEngine *>(_o);
    if (_c == QMetaObject::InvokeMetaMethod) {
        switch (_id) {
        case 0: _t->go(); break;
        case 1: _t->quit(); break;
        case 2: _t->kill(); break;
        case 3: _t->onTimeout(); break;
        case 4: _t->onReadyRead(); break;
        case 5: _t->onPingTimeout(); break;
        case 6: _t->onIdleTimeout(); break;
        case 7: _t->pong((*reinterpret_cast<std::add_pointer_t<bool>>(_a[1]))); break;
        case 8: _t->pong(); break;
        case 9: _t->onProtocolStart(); break;
        case 10: _t->flushWriteBuffer(); break;
        case 11: _t->clearWriteBuffer(); break;
        case 12: _t->onQuitTimeout(); break;
        case 13: _t->onProtocolStartTimeout(); break;
        default: ;
        }
    }
}

const QMetaObject *ChessEngine::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *ChessEngine::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_staticMetaObjectStaticContent<qt_meta_tag_ZN11ChessEngineE_t>.strings))
        return static_cast<void*>(this);
    return ChessPlayer::qt_metacast(_clname);
}

int ChessEngine::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = ChessPlayer::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 14)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 14;
    }
    if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 14)
            *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType();
        _id -= 14;
    }
    return _id;
}
QT_WARNING_POP
