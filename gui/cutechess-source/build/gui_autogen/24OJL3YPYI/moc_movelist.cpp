/****************************************************************************
** Meta object code from reading C++ file 'movelist.h'
**
** Created by: The Qt Meta Object Compiler version 69 (Qt 6.12.0)
**
** WARNING! All changes made in this file will be lost!
*****************************************************************************/

#include "../../../projects/gui/src/movelist.h"
#include <QtGui/qtextcursor.h>
#include <QtCore/qmetatype.h>

#include <QtCore/qtmochelpers.h>

#include <memory>


#include <QtCore/qxptype_traits.h>
#if !defined(Q_MOC_OUTPUT_REVISION)
#error "The header file 'movelist.h' doesn't include <QObject>."
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
struct qt_meta_tag_ZN8MoveListE_t {};
} // unnamed namespace

template <> constexpr inline auto MoveList::qt_create_metaobjectdata<qt_meta_tag_ZN8MoveListE_t>()
{
    namespace QMC = QtMocConstants;
    QtMocHelpers::StringRefStorage qt_stringData {
        "MoveList",
        "moveClicked",
        "",
        "num",
        "keyLeft",
        "commentClicked",
        "comment",
        "selectMove",
        "moveNum",
        "setMove",
        "ply",
        "Chess::GenericMove",
        "move",
        "sanString",
        "onMoveMade",
        "onLinkClicked",
        "QUrl",
        "url",
        "selectChosenMove",
        "onContextMenuRequest"
    };

    QtMocHelpers::UintData qt_methods {
        // Signal 'moveClicked'
        QtMocHelpers::SignalData<void(int, bool)>(1, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 3 }, { QMetaType::Bool, 4 },
        }}),
        // Signal 'commentClicked'
        QtMocHelpers::SignalData<void(int, const QString &)>(5, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 3 }, { QMetaType::QString, 6 },
        }}),
        // Slot 'selectMove'
        QtMocHelpers::SlotData<bool(int)>(7, 2, QMC::AccessPublic, QMetaType::Bool, {{
            { QMetaType::Int, 8 },
        }}),
        // Slot 'setMove'
        QtMocHelpers::SlotData<void(int, const Chess::GenericMove &, const QString &, const QString &)>(9, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 10 }, { 0x80000000 | 11, 12 }, { QMetaType::QString, 13 }, { QMetaType::QString, 6 },
        }}),
        // Slot 'onMoveMade'
        QtMocHelpers::SlotData<void(const Chess::GenericMove &, const QString &, const QString &)>(14, 2, QMC::AccessPrivate, QMetaType::Void, {{
            { 0x80000000 | 11, 12 }, { QMetaType::QString, 13 }, { QMetaType::QString, 6 },
        }}),
        // Slot 'onLinkClicked'
        QtMocHelpers::SlotData<void(const QUrl &)>(15, 2, QMC::AccessPrivate, QMetaType::Void, {{
            { 0x80000000 | 16, 17 },
        }}),
        // Slot 'selectChosenMove'
        QtMocHelpers::SlotData<void()>(18, 2, QMC::AccessPrivate, QMetaType::Void),
        // Slot 'onContextMenuRequest'
        QtMocHelpers::SlotData<void()>(19, 2, QMC::AccessPrivate, QMetaType::Void),
    };
    QtMocHelpers::UintData qt_properties {
    };
    QtMocHelpers::UintData qt_enums {
    };
    return QtMocHelpers::metaObjectData<MoveList, qt_meta_tag_ZN8MoveListE_t>(QMC::MetaObjectFlag{}, qt_stringData,
            qt_methods, qt_properties, qt_enums);
}
Q_CONSTINIT const QMetaObject MoveList::staticMetaObject = { {
    QMetaObject::SuperData::link<QWidget::staticMetaObject>(),
    qt_staticMetaObjectStaticContent<qt_meta_tag_ZN8MoveListE_t>.stringdata,
    qt_staticMetaObjectStaticContent<qt_meta_tag_ZN8MoveListE_t>.data,
    qt_static_metacall,
    nullptr,
    qt_staticMetaObjectRelocatingContent<qt_meta_tag_ZN8MoveListE_t>.metaTypes,
    nullptr
} };

void MoveList::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    auto *_t = static_cast<MoveList *>(_o);
    if (_c == QMetaObject::InvokeMetaMethod) {
        switch (_id) {
        case 0: _t->moveClicked((*reinterpret_cast<std::add_pointer_t<int>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<bool>>(_a[2]))); break;
        case 1: _t->commentClicked((*reinterpret_cast<std::add_pointer_t<int>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[2]))); break;
        case 2: { bool _r = _t->selectMove((*reinterpret_cast<std::add_pointer_t<int>>(_a[1])));
            if (_a[0]) *reinterpret_cast<bool*>(_a[0]) = std::move(_r); }  break;
        case 3: _t->setMove((*reinterpret_cast<std::add_pointer_t<int>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<Chess::GenericMove>>(_a[2])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[3])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[4]))); break;
        case 4: _t->onMoveMade((*reinterpret_cast<std::add_pointer_t<Chess::GenericMove>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[2])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[3]))); break;
        case 5: _t->onLinkClicked((*reinterpret_cast<std::add_pointer_t<QUrl>>(_a[1]))); break;
        case 6: _t->selectChosenMove(); break;
        case 7: _t->onContextMenuRequest(); break;
        default: ;
        }
    }
    if (_c == QMetaObject::IndexOfMethod) {
        if (QtMocHelpers::indexOfMethod<void (MoveList::*)(int , bool )>(_a, &MoveList::moveClicked, 0))
            return;
        if (QtMocHelpers::indexOfMethod<void (MoveList::*)(int , const QString & )>(_a, &MoveList::commentClicked, 1))
            return;
    }
}

const QMetaObject *MoveList::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *MoveList::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_staticMetaObjectStaticContent<qt_meta_tag_ZN8MoveListE_t>.strings))
        return static_cast<void*>(this);
    return QWidget::qt_metacast(_clname);
}

int MoveList::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = QWidget::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 8)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 8;
    }
    if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 8)
            *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType();
        _id -= 8;
    }
    return _id;
}

// SIGNAL 0
void MoveList::moveClicked(int _t1, bool _t2)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 0, nullptr, _t1, _t2);
}

// SIGNAL 1
void MoveList::commentClicked(int _t1, const QString & _t2)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 1, nullptr, _t1, _t2);
}
QT_WARNING_POP
