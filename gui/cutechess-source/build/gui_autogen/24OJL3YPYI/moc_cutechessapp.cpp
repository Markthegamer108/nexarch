/****************************************************************************
** Meta object code from reading C++ file 'cutechessapp.h'
**
** Created by: The Qt Meta Object Compiler version 69 (Qt 6.12.0)
**
** WARNING! All changes made in this file will be lost!
*****************************************************************************/

#include "../../../projects/gui/src/cutechessapp.h"
#include <QtCore/qmetatype.h>

#include <QtCore/qtmochelpers.h>

#include <memory>


#include <QtCore/qxptype_traits.h>
#if !defined(Q_MOC_OUTPUT_REVISION)
#error "The header file 'cutechessapp.h' doesn't include <QObject>."
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
struct qt_meta_tag_ZN20CuteChessApplicationE_t {};
} // unnamed namespace

template <> constexpr inline auto CuteChessApplication::qt_create_metaobjectdata<qt_meta_tag_ZN20CuteChessApplicationE_t>()
{
    namespace QMC = QtMocConstants;
    QtMocHelpers::StringRefStorage qt_stringData {
        "CuteChessApplication",
        "newGameWindow",
        "MainWindow*",
        "",
        "ChessGame*",
        "game",
        "newDefaultGame",
        "showSettingsDialog",
        "showTournamentResultsDialog",
        "showGameDatabaseDialog",
        "showGameWall",
        "closeDialogs",
        "onQuitAction",
        "onLastWindowClosed",
        "onAboutToQuit"
    };

    QtMocHelpers::UintData qt_methods {
        // Slot 'newGameWindow'
        QtMocHelpers::SlotData<MainWindow *(ChessGame *)>(1, 3, QMC::AccessPublic, 0x80000000 | 2, {{
            { 0x80000000 | 4, 5 },
        }}),
        // Slot 'newDefaultGame'
        QtMocHelpers::SlotData<void()>(6, 3, QMC::AccessPublic, QMetaType::Void),
        // Slot 'showSettingsDialog'
        QtMocHelpers::SlotData<void()>(7, 3, QMC::AccessPublic, QMetaType::Void),
        // Slot 'showTournamentResultsDialog'
        QtMocHelpers::SlotData<void()>(8, 3, QMC::AccessPublic, QMetaType::Void),
        // Slot 'showGameDatabaseDialog'
        QtMocHelpers::SlotData<void()>(9, 3, QMC::AccessPublic, QMetaType::Void),
        // Slot 'showGameWall'
        QtMocHelpers::SlotData<void()>(10, 3, QMC::AccessPublic, QMetaType::Void),
        // Slot 'closeDialogs'
        QtMocHelpers::SlotData<void()>(11, 3, QMC::AccessPublic, QMetaType::Void),
        // Slot 'onQuitAction'
        QtMocHelpers::SlotData<void()>(12, 3, QMC::AccessPublic, QMetaType::Void),
        // Slot 'onLastWindowClosed'
        QtMocHelpers::SlotData<void()>(13, 3, QMC::AccessPrivate, QMetaType::Void),
        // Slot 'onAboutToQuit'
        QtMocHelpers::SlotData<void()>(14, 3, QMC::AccessPrivate, QMetaType::Void),
    };
    QtMocHelpers::UintData qt_properties {
    };
    QtMocHelpers::UintData qt_enums {
    };
    return QtMocHelpers::metaObjectData<CuteChessApplication, qt_meta_tag_ZN20CuteChessApplicationE_t>(QMC::MetaObjectFlag{}, qt_stringData,
            qt_methods, qt_properties, qt_enums);
}
Q_CONSTINIT const QMetaObject CuteChessApplication::staticMetaObject = { {
    QMetaObject::SuperData::link<QApplication::staticMetaObject>(),
    qt_staticMetaObjectStaticContent<qt_meta_tag_ZN20CuteChessApplicationE_t>.stringdata,
    qt_staticMetaObjectStaticContent<qt_meta_tag_ZN20CuteChessApplicationE_t>.data,
    qt_static_metacall,
    nullptr,
    qt_staticMetaObjectRelocatingContent<qt_meta_tag_ZN20CuteChessApplicationE_t>.metaTypes,
    nullptr
} };

void CuteChessApplication::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    auto *_t = static_cast<CuteChessApplication *>(_o);
    if (_c == QMetaObject::InvokeMetaMethod) {
        switch (_id) {
        case 0: { MainWindow* _r = _t->newGameWindow((*reinterpret_cast<std::add_pointer_t<ChessGame*>>(_a[1])));
            if (_a[0]) *reinterpret_cast<MainWindow**>(_a[0]) = std::move(_r); }  break;
        case 1: _t->newDefaultGame(); break;
        case 2: _t->showSettingsDialog(); break;
        case 3: _t->showTournamentResultsDialog(); break;
        case 4: _t->showGameDatabaseDialog(); break;
        case 5: _t->showGameWall(); break;
        case 6: _t->closeDialogs(); break;
        case 7: _t->onQuitAction(); break;
        case 8: _t->onLastWindowClosed(); break;
        case 9: _t->onAboutToQuit(); break;
        default: ;
        }
    }
}

const QMetaObject *CuteChessApplication::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *CuteChessApplication::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_staticMetaObjectStaticContent<qt_meta_tag_ZN20CuteChessApplicationE_t>.strings))
        return static_cast<void*>(this);
    return QApplication::qt_metacast(_clname);
}

int CuteChessApplication::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = QApplication::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 10)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 10;
    }
    if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 10)
            *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType();
        _id -= 10;
    }
    return _id;
}
QT_WARNING_POP
