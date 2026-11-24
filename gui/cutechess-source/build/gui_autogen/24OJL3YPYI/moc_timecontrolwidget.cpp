/****************************************************************************
** Meta object code from reading C++ file 'timecontrolwidget.h'
**
** Created by: The Qt Meta Object Compiler version 69 (Qt 6.12.0)
**
** WARNING! All changes made in this file will be lost!
*****************************************************************************/

#include "../../../projects/gui/src/timecontrolwidget.h"
#include <QtCore/qmetatype.h>

#include <QtCore/qtmochelpers.h>

#include <memory>


#include <QtCore/qxptype_traits.h>
#if !defined(Q_MOC_OUTPUT_REVISION)
#error "The header file 'timecontrolwidget.h' doesn't include <QObject>."
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
struct qt_meta_tag_ZN17TimeControlWidgetE_t {};
} // unnamed namespace

template <> constexpr inline auto TimeControlWidget::qt_create_metaobjectdata<qt_meta_tag_ZN17TimeControlWidgetE_t>()
{
    namespace QMC = QtMocConstants;
    QtMocHelpers::StringRefStorage qt_stringData {
        "TimeControlWidget",
        "timeControlModeChanged",
        "",
        "Mode",
        "mode",
        "setTimeControlMode",
        "onOtherTimeControlModeChanged",
        "Tournament",
        "TimePerMove",
        "Infinite",
        "Hourglass"
    };

    QtMocHelpers::UintData qt_methods {
        // Signal 'timeControlModeChanged'
        QtMocHelpers::SignalData<void(enum Mode)>(1, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 3, 4 },
        }}),
        // Slot 'setTimeControlMode'
        QtMocHelpers::SlotData<void(enum Mode)>(5, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 3, 4 },
        }}),
        // Slot 'onOtherTimeControlModeChanged'
        QtMocHelpers::SlotData<void(enum Mode)>(6, 2, QMC::AccessPrivate, QMetaType::Void, {{
            { 0x80000000 | 3, 4 },
        }}),
    };
    QtMocHelpers::UintData qt_properties {
    };
    QtMocHelpers::UintData qt_enums {
        // enum 'Mode'
        QtMocHelpers::EnumData<enum Mode>(3, 3, QMC::EnumFlags{}).add({
            {    7, Mode::Tournament },
            {    8, Mode::TimePerMove },
            {    9, Mode::Infinite },
            {   10, Mode::Hourglass },
        }),
    };
    return QtMocHelpers::metaObjectData<TimeControlWidget, qt_meta_tag_ZN17TimeControlWidgetE_t>(QMC::MetaObjectFlag{}, qt_stringData,
            qt_methods, qt_properties, qt_enums);
}
Q_CONSTINIT const QMetaObject TimeControlWidget::staticMetaObject = { {
    QMetaObject::SuperData::link<QWidget::staticMetaObject>(),
    qt_staticMetaObjectStaticContent<qt_meta_tag_ZN17TimeControlWidgetE_t>.stringdata,
    qt_staticMetaObjectStaticContent<qt_meta_tag_ZN17TimeControlWidgetE_t>.data,
    qt_static_metacall,
    nullptr,
    qt_staticMetaObjectRelocatingContent<qt_meta_tag_ZN17TimeControlWidgetE_t>.metaTypes,
    nullptr
} };

void TimeControlWidget::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    auto *_t = static_cast<TimeControlWidget *>(_o);
    if (_c == QMetaObject::InvokeMetaMethod) {
        switch (_id) {
        case 0: _t->timeControlModeChanged((*reinterpret_cast<std::add_pointer_t<enum Mode>>(_a[1]))); break;
        case 1: _t->setTimeControlMode((*reinterpret_cast<std::add_pointer_t<enum Mode>>(_a[1]))); break;
        case 2: _t->onOtherTimeControlModeChanged((*reinterpret_cast<std::add_pointer_t<enum Mode>>(_a[1]))); break;
        default: ;
        }
    }
    if (_c == QMetaObject::IndexOfMethod) {
        if (QtMocHelpers::indexOfMethod<void (TimeControlWidget::*)(Mode )>(_a, &TimeControlWidget::timeControlModeChanged, 0))
            return;
    }
}

const QMetaObject *TimeControlWidget::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *TimeControlWidget::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_staticMetaObjectStaticContent<qt_meta_tag_ZN17TimeControlWidgetE_t>.strings))
        return static_cast<void*>(this);
    return QWidget::qt_metacast(_clname);
}

int TimeControlWidget::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = QWidget::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 3)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 3;
    }
    if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 3)
            *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType();
        _id -= 3;
    }
    return _id;
}

// SIGNAL 0
void TimeControlWidget::timeControlModeChanged(Mode _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 0, nullptr, _t1);
}
QT_WARNING_POP
